"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de cuentas.

EN: This module implements business services and transactional effects for the accounts domain.

Contexto existente / Existing context:
Transactional business services for the accounts domain.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.accounts.forms import BRANCH_REQUIRED_ROLE_CODES
from apps.accounts.models import Role, UserRole
from apps.accounts.scopes import accessible_branch_ids, role_binding_in_authority
from apps.audit.services import audit_log

User = get_user_model()

MANAGEMENT_PERMISSION_CODES = ("accounts.manage_users", "accounts.assign_roles")


def _require_branch_scope(*, actor, permission_codes, branch) -> None:
    if branch is None:
        return
    branch_ids = accessible_branch_ids(actor, permission_codes=permission_codes)
    if branch_ids is not None and branch.pk not in branch_ids:
        raise PermissionDenied("No tienes permiso para gestionar usuarios en esta sucursal.")


def _require_user_scope(*, actor, user, permission_codes=MANAGEMENT_PERMISSION_CODES) -> None:
    if actor is None or not getattr(actor, "is_authenticated", False):
        raise PermissionDenied("No tienes permiso para gestionar este usuario.")
    branch_ids = accessible_branch_ids(actor, permission_codes=permission_codes)
    if branch_ids is None:
        return
    from apps.accounts.selectors import manageable_users_queryset

    if not manageable_users_queryset(actor).filter(pk=user.pk).exists():
        raise PermissionDenied("No tienes permiso para gestionar este usuario.")


def user_operational_branch(user):
    """Return the first active branch tied to an operational role.

    Sales, invoices and stock modules can use this helper to attribute an action to
    the branch where the worker was operating. The user's optional main branch is a
    fallback only; role-level branch assignment remains the authoritative source.
    """
    user_role = (
        user.user_roles.filter(is_active=True, role__code__in=BRANCH_REQUIRED_ROLE_CODES, branch__isnull=False)
        .select_related("branch", "role")
        .order_by("role__level", "id")
        .first()
    )
    if user_role:
        return user_role.branch
    return getattr(user, "branch", None)


@transaction.atomic
def create_internal_user(*, actor, form):
    _require_branch_scope(actor=actor, permission_codes=MANAGEMENT_PERMISSION_CODES, branch=form.cleaned_data.get("branch"))
    user = form.save(commit=False)
    password = form.cleaned_data["password1"]
    validate_password(password, user=user)
    user.set_password(password)
    user.last_password_change_at = timezone.now()
    user.save()
    audit_log(user=actor, action="accounts.user.create", target=user, after={"username": user.username, "email": user.email})
    return user


@transaction.atomic
def update_internal_user(*, actor, user, form):
    _require_user_scope(actor=actor, user=user)
    _require_branch_scope(actor=actor, permission_codes=MANAGEMENT_PERMISSION_CODES, branch=form.cleaned_data.get("branch"))
    before = {
        "email": user.email,
        "is_active": user.is_active,
        "branch_id": user.branch_id,
        "must_change_password": user.must_change_password,
    }
    user = form.save()
    after = {
        "email": user.email,
        "is_active": user.is_active,
        "branch_id": user.branch_id,
        "must_change_password": user.must_change_password,
    }
    audit_log(user=actor, action="accounts.user.update", target=user, before=before, after=after)
    return user


@transaction.atomic
def assign_role_to_user(*, actor, user, role: Role, branch=None, starts_at=None, expires_at=None):
    _require_user_scope(actor=actor, user=user)
    _require_branch_scope(actor=actor, permission_codes=("accounts.assign_roles",), branch=branch)
    if role.code in BRANCH_REQUIRED_ROLE_CODES and branch is None:
        raise ValueError("Los roles operativos requieren sucursal específica.")
    if not role_binding_in_authority(actor=actor, role=role, branch=branch):
        raise PermissionDenied("No tienes autoridad para asignar este rol en este alcance.")

    user_role, created = UserRole.objects.update_or_create(
        user=user,
        role=role,
        branch=branch,
        defaults={
            "is_active": True,
            "starts_at": starts_at,
            "expires_at": expires_at,
            "assigned_by": actor if getattr(actor, "is_authenticated", False) else None,
        },
    )
    audit_log(
        user=actor,
        action="accounts.role.assign",
        target=user,
        after={"role": role.code, "branch_id": branch.pk if branch else None, "created": created},
    )
    return user_role


@transaction.atomic
def remove_user_role(*, actor, user_role: UserRole):
    _require_user_scope(actor=actor, user=user_role.user)
    if not role_binding_in_authority(actor=actor, role=user_role.role, branch=user_role.branch):
        raise PermissionDenied("No tienes autoridad para retirar esta asignación.")
    user = user_role.user
    before = {"role": user_role.role.code, "branch_id": user_role.branch_id, "is_active": user_role.is_active}
    user_role.is_active = False
    user_role.save(update_fields=["is_active", "updated_at"])
    audit_log(user=actor, action="accounts.role.remove", target=user, before=before, after={"is_active": False})
    return user_role


@transaction.atomic
def toggle_user_active_state(*, actor, user):
    _require_user_scope(actor=actor, user=user)
    before = {"is_active": user.is_active}
    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])
    audit_log(user=actor, action="accounts.user.toggle_active", target=user, before=before, after={"is_active": user.is_active})
    return user


@transaction.atomic
def set_user_password_by_admin(*, actor, user, password: str, must_change_password: bool = True):
    _require_user_scope(actor=actor, user=user)
    validate_password(password, user=user)
    from apps.security_center.services import set_password_securely
    return set_password_securely(
        actor=actor, user=user, password=password, must_change_password=must_change_password, action="accounts.password.admin_set"
    )
