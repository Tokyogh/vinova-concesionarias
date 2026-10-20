"""ES: Este módulo implementa el componente client services para el dominio de cuentas.

EN: This module implements the client services component for the accounts domain.

Contexto existente / Existing context:
Client services support for the accounts domain.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.models import ClientInvitation, Role, UserRole
from apps.accounts.scopes import accessible_branch_ids
from apps.audit.services import audit_log
from apps.customers.models import Customer

User = get_user_model()


def _token_digest(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _new_token() -> str:
    return secrets.token_urlsafe(32)


def _client_role() -> Role:
    role = (
        Role.objects.filter(code="cliente", is_active=True, permissions__code="portal.access")
        .distinct()
        .first()
    )
    if role is None:
        raise ValidationError("El rol de cliente y el permiso portal.access deben estar configurados.")
    return role


def _grant_client_role(*, user, actor=None) -> UserRole:
    role = _client_role()
    assignment, _ = UserRole.objects.update_or_create(
        user=user,
        role=role,
        branch=None,
        defaults={"is_active": True, "starts_at": None, "expires_at": None, "assigned_by": actor},
    )
    return assignment


def _unique_username(email: str) -> str:
    base = slugify(email.split("@", 1)[0]).replace("-", "_")[:130] or "cliente"
    candidate = base
    suffix = 1
    while User.objects.filter(username=candidate).exists():
        suffix += 1
        candidate = f"{base[:140 - len(str(suffix))]}_{suffix}"
    return candidate


def _create_invitation(*, customer, email, kind, user=None, actor=None, valid_days=7):
    ClientInvitation.objects.filter(
        customer=customer, status=ClientInvitation.Status.PENDING
    ).update(status=ClientInvitation.Status.REVOKED)
    raw_token = _new_token()
    invitation = ClientInvitation.objects.create(
        customer=customer,
        user=user,
        email=email,
        token_digest=_token_digest(raw_token),
        kind=kind,
        expires_at=timezone.now() + timedelta(days=valid_days),
        invited_by=actor,
    )
    return invitation, raw_token


@transaction.atomic
def create_staff_client_invitation(*, actor, customer: Customer):
    customer = Customer.objects.select_for_update().get(pk=customer.pk, is_deleted=False)
    branch_ids = accessible_branch_ids(actor, permission_codes=("customers.manage",))
    if branch_ids is not None and (
        customer.assigned_branch_id is None or customer.assigned_branch_id not in branch_ids
    ):
        raise ValidationError("No tienes permiso para invitar clientes de esta sucursal.")
    if customer.account_id:
        raise ValidationError("El cliente ya tiene una cuenta vinculada.")
    email = (customer.email or "").strip().lower()
    if not email:
        raise ValidationError("Registra un correo en el expediente antes de enviar la invitación.")
    if User.objects.filter(email__iexact=email).exists():
        raise ValidationError("Ya existe una cuenta con ese correo; revísala antes de vincularla.")
    _client_role()
    invitation, raw_token = _create_invitation(
        customer=customer,
        email=email,
        kind=ClientInvitation.Kind.STAFF_INVITATION,
        actor=actor,
    )
    audit_log(
        user=actor,
        action="accounts.client_invitation.create",
        target=customer,
        customer=customer,
        after={"invitation": invitation.pk, "expires_at": invitation.expires_at.isoformat()},
        is_sensitive=True,
    )
    return invitation, raw_token


@transaction.atomic
def create_client_registration(*, cleaned_data: dict):
    email = cleaned_data["email"].strip().lower()
    _client_role()
    if User.objects.filter(email__iexact=email).exists() or Customer.objects.filter(email__iexact=email).exists():
        raise ValidationError(
            "No fue posible completar el registro. Si ya eres cliente, solicita una invitación a la concesionaria."
        )
    user = User.objects.create_user(
        username=_unique_username(email),
        email=email,
        first_name=cleaned_data["first_name"].strip(),
        last_name=cleaned_data["last_name"].strip(),
        phone=cleaned_data.get("phone", "").strip(),
        password=cleaned_data["password1"],
        is_active=False,
    )
    user.last_password_change_at = timezone.now()
    user.save(update_fields=["last_password_change_at"])
    _grant_client_role(user=user)
    customer = Customer.objects.create(
        first_name=user.first_name,
        last_name=user.last_name,
        email=email,
        phone=user.phone,
        preferred_contact_method=Customer.ContactMethod.EMAIL,
        source="registro_web",
        status=Customer.Status.ACTIVE,
        account=user,
    )
    invitation, raw_token = _create_invitation(
        customer=customer,
        email=email,
        user=user,
        kind=ClientInvitation.Kind.REGISTRATION_ACTIVATION,
    )
    audit_log(
        user=None,
        action="accounts.client_registration.create",
        target=customer,
        customer=customer,
        after={
            "user": user.pk,
            "invitation": invitation.pk,
            "terms_accepted": bool(cleaned_data.get("accept_terms")),
            "terms_version": settings.VINOVA_TERMS_VERSION,
            "privacy_notice_acknowledged": bool(cleaned_data.get("privacy_acknowledgement")),
            "privacy_notice_version": settings.VINOVA_PRIVACY_NOTICE_VERSION,
        },
        is_sensitive=True,
    )
    return invitation, raw_token


def get_client_invitation(raw_token: str) -> ClientInvitation:
    if not raw_token or len(raw_token) > 200:
        raise ValidationError("La invitación no es válida.")
    invitation = (
        ClientInvitation.objects.select_related("customer", "user")
        .filter(token_digest=_token_digest(raw_token))
        .first()
    )
    if invitation is None or invitation.status != ClientInvitation.Status.PENDING:
        raise ValidationError("La invitación no es válida o ya fue utilizada.")
    if invitation.is_expired:
        raise ValidationError("La invitación ha caducado. Solicita una nueva.")
    return invitation


@transaction.atomic
def accept_client_invitation(*, raw_token: str, password: str | None = None):
    invitation = ClientInvitation.objects.select_for_update().filter(
        token_digest=_token_digest(raw_token)
    ).first()
    if invitation is None or invitation.status != ClientInvitation.Status.PENDING:
        raise ValidationError("La invitación no es válida o ya fue utilizada.")
    if invitation.is_expired:
        raise ValidationError("La invitación ha caducado. Solicita una nueva.")
    customer = Customer.objects.select_for_update().get(pk=invitation.customer_id, is_deleted=False)

    if invitation.kind == ClientInvitation.Kind.STAFF_INVITATION:
        if customer.account_id:
            raise ValidationError("El cliente ya tiene una cuenta vinculada.")
        if not password:
            raise ValidationError("Define una contraseña para completar la invitación.")
        if User.objects.filter(email__iexact=invitation.email).exists():
            raise ValidationError("Ya existe una cuenta con ese correo.")
        user = User.objects.create_user(
            username=_unique_username(invitation.email),
            email=invitation.email,
            first_name=customer.first_name,
            last_name=customer.last_name,
            phone=customer.phone,
            password=password,
            is_active=True,
        )
        user.last_password_change_at = timezone.now()
        user.save(update_fields=["last_password_change_at"])
        _grant_client_role(user=user, actor=invitation.invited_by)
        customer.account = user
        customer.save(update_fields=["account", "updated_at"])
        invitation.user = user
    else:
        user = invitation.user
        if user is None or customer.account_id != user.pk:
            raise ValidationError("La activación no corresponde a una cuenta válida.")
        user.is_active = True
        user.save(update_fields=["is_active"])

    invitation.status = ClientInvitation.Status.ACCEPTED
    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=["user", "status", "accepted_at", "updated_at"])
    audit_log(
        user=user,
        action="accounts.client_invitation.accept",
        target=customer,
        customer=customer,
        before={"invitation_status": ClientInvitation.Status.PENDING},
        after={"invitation_status": ClientInvitation.Status.ACCEPTED, "user": user.pk},
        is_sensitive=True,
    )
    return user


def send_client_access_email(*, invitation: ClientInvitation, raw_token: str, accept_url: str) -> int:
    if invitation.kind == ClientInvitation.Kind.REGISTRATION_ACTIVATION:
        subject = "Activa tu cuenta de cliente en Vinova"
        intro = "Confirma tu correo para activar la cuenta que acabas de registrar."
    else:
        subject = "Invitación al portal de clientes de Vinova"
        intro = "La concesionaria te invitó a crear tu acceso privado como cliente."
    body = f"{intro}\n\nContinúa aquí: {accept_url}\n\nEl enlace caduca el {invitation.expires_at:%d/%m/%Y %H:%M}."
    return send_mail(subject, body, None, [invitation.email], fail_silently=True)
