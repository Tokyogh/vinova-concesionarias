"""ES: Este módulo implementa el componente qa client services para el dominio de cuentas.

EN: This module implements the qa client services component for the accounts domain.

Contexto existente / Existing context:
Qa client services support for the accounts domain.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounts.models import User
from apps.accounts.scopes import accessible_branch_ids
from apps.customers.models import Customer
from apps.customers.services import create_customer_from_data, link_customer_account

QA_PORTAL_SOURCE = "qa_portal_compatibility"
PORTAL_CUSTOMER_STATUSES = (Customer.Status.ACTIVE, Customer.Status.VIP)


@dataclass(frozen=True)
class QAClientPreparationResult:
    customer: Customer
    created: bool


def _validate_actor(*, actor: User, branch_id: int | None) -> None:
    if not actor.is_active or not actor.has_perm_code("customers.manage"):
        raise ValidationError("El operador no tiene permiso vigente para gestionar clientes.")
    branch_ids = accessible_branch_ids(actor, permission_codes=("customers.manage",))
    if branch_ids is not None and (branch_id is None or branch_id not in branch_ids):
        raise ValidationError("El operador no tiene alcance sobre la sucursal de la cuenta.")


def _validate_target(*, user: User) -> None:
    if not user.is_active:
        raise ValidationError("La cuenta QA está inactiva.")
    if user.is_staff or user.is_superuser:
        raise ValidationError("No se preparan expedientes QA para cuentas Staff o superusuario.")
    if not user.has_role("cliente") or not user.has_perm_code("portal.access"):
        raise ValidationError("La cuenta no tiene rol cliente y permiso de portal vigentes.")


def validate_qa_client_account(*, actor: User, user: User) -> Customer | None:
    """Validate an explicit QA preparation target without changing data."""
    _validate_actor(actor=actor, branch_id=user.branch_id)
    _validate_target(user=user)

    linked = Customer.objects.filter(account=user).first()
    if linked is not None:
        if linked.is_deleted or linked.status not in PORTAL_CUSTOMER_STATUSES:
            raise ValidationError(
                "La cuenta ya tiene un expediente no disponible; debe revisarse y activarse por el flujo empresarial."
            )
        return linked

    if user.email and Customer.objects.filter(email__iexact=user.email).exists():
        raise ValidationError(
            "Existe al menos un expediente candidato; la asociación es ambigua y no fue modificada."
        )
    return None


@transaction.atomic
def prepare_qa_client_account(*, actor: User, user: User) -> QAClientPreparationResult:
    """Create and link one explicitly selected QA profile without identity guessing.

    The caller must enforce the non-production boundary. Existing Customer rows
    are never selected by email, identification number, or name: an email match
    is treated only as an ambiguity and aborts the operation.
    """
    actor = User.objects.select_for_update().get(pk=actor.pk)
    user = User.objects.select_for_update().get(pk=user.pk)
    linked = validate_qa_client_account(actor=actor, user=user)
    if linked is not None:
        return QAClientPreparationResult(customer=linked, created=False)

    customer = create_customer_from_data(
        actor=actor,
        validated_data={
            "first_name": user.first_name or "QA",
            "last_name": user.last_name or f"Cliente {user.pk}",
            "email": user.email,
            "source": QA_PORTAL_SOURCE,
            "status": Customer.Status.ACTIVE,
            "assigned_branch": user.branch,
        },
    )
    customer = link_customer_account(actor=actor, customer=customer, user=user)
    return QAClientPreparationResult(customer=customer, created=True)
