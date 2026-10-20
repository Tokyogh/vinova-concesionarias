"""ES: Este módulo implementa el componente scopes para el dominio de cuentas.

EN: This module implements the scopes component for the accounts domain.

Contexto existente / Existing context:
Scopes support for the accounts domain.
"""

from __future__ import annotations

from collections.abc import Iterable

from django.db.models import Q
from django.db.models import QuerySet
from django.utils import timezone


def active_role_assignments(user, *, permission_codes: Iterable[str] | None = None) -> QuerySet:
    qs = user.active_role_assignments()
    if permission_codes:
        qs = qs.filter(role__permissions__code__in=tuple(permission_codes))
    return qs.distinct()


def accessible_branch_ids(user, *, permission_codes: Iterable[str]) -> tuple[int, ...] | None:
    if not user or not getattr(user, "is_authenticated", False) or not getattr(user, "is_active", False):
        return ()
    if user.is_superuser:
        return None
    assignments = active_role_assignments(user, permission_codes=permission_codes)
    if assignments.filter(branch__isnull=True).exists():
        return None
    return tuple(assignments.exclude(branch__isnull=True).values_list("branch_id", flat=True).distinct())


def has_global_permission(user, permission_code: str) -> bool:
    return accessible_branch_ids(user, permission_codes=(permission_code,)) is None


def accessible_management_branch_ids(user) -> tuple[int, ...] | None:
    return accessible_branch_ids(user, permission_codes=("accounts.manage_users", "accounts.assign_roles"))


def _strongest_role_level(user) -> int | None:
    levels = list(user.active_role_assignments().values_list("role__level", flat=True))
    if not levels:
        return None
    return min(levels)


def assignable_role_queryset_for(user):
    """Active roles the actor may assign, derived from the role hierarchy.

    The actor cannot grant a role strictly more privileged (lower level) than
    their own strongest role. Superuser keeps full reach.
    """
    from apps.accounts.models import Role

    qs = Role.objects.filter(is_active=True)
    if not getattr(user, "is_active", False):
        return qs.none()
    if user.is_superuser:
        return qs
    strongest = _strongest_role_level(user)
    if strongest is None:
        return qs.none()
    return qs.filter(level__gte=strongest)


def role_binding_in_authority(*, actor, role, branch) -> bool:
    """Whether the actor may create or remove the (role, branch) binding.

    A binding is within authority when:
    - the assignment branch is covered by the actor's accounts.assign_roles
      scope (a global binding requires a global assign scope), and
    - the role is not strictly more privileged than the actor's strongest role.
    """
    if (
        actor is None
        or not getattr(actor, "is_authenticated", False)
        or not getattr(actor, "is_active", False)
    ):
        return False
    if actor.is_superuser:
        return True
    branch_ids = accessible_branch_ids(actor, permission_codes=("accounts.assign_roles",))
    if branch is None:
        if branch_ids is not None:
            return False
    elif branch_ids is not None and branch.pk not in branch_ids:
        return False
    strongest = _strongest_role_level(actor)
    if strongest is None or role.level < strongest:
        return False
    return True


def scope_queryset_to_user_branches(queryset: QuerySet, *, user, permission_codes: Iterable[str], branch_lookup: str = "branch") -> QuerySet:
    branch_ids = accessible_branch_ids(user, permission_codes=permission_codes)
    if branch_ids is None:
        return queryset
    if not branch_ids:
        return queryset.none()
    return queryset.filter(**{f"{branch_lookup}_id__in": branch_ids})


def accessible_branches_queryset(user, *, permission_codes: Iterable[str], active_only: bool = True) -> QuerySet:
    from apps.branches.models import Branch

    qs = Branch.objects.all()
    if active_only:
        qs = qs.filter(is_active=True)
    branch_ids = accessible_branch_ids(user, permission_codes=permission_codes)
    if branch_ids is not None:
        qs = qs.filter(id__in=branch_ids)
    return qs.select_related("company").order_by("company__commercial_name", "name")


def accessible_users_queryset(user, *, permission_codes: Iterable[str], active_only: bool = True) -> QuerySet:
    from apps.accounts.models import User

    qs = User.objects.all()
    if active_only:
        qs = qs.filter(is_active=True)
    branch_ids = accessible_branch_ids(user, permission_codes=permission_codes)
    now = timezone.now()
    role_filters = {
        "user_roles__is_active": True,
        "user_roles__role__is_active": True,
    }
    if branch_ids is not None:
        if not branch_ids:
            return qs.none()
        return users_in_branches_queryset(branch_ids, active_only=active_only)
    qs = qs.filter(
        Q(user_roles__starts_at__isnull=True) | Q(user_roles__starts_at__lte=now),
        Q(user_roles__expires_at__isnull=True) | Q(user_roles__expires_at__gt=now),
        **role_filters,
    )
    return qs.distinct().order_by("first_name", "last_name", "username")


def users_in_branches_queryset(branch_ids: Iterable[int], *, active_only: bool = True) -> QuerySet:
    from apps.accounts.models import User

    qs = User.objects.all()
    if active_only:
        qs = qs.filter(is_active=True)
    now = timezone.now()
    return (
        qs.filter(
            Q(user_roles__starts_at__isnull=True) | Q(user_roles__starts_at__lte=now),
            Q(user_roles__expires_at__isnull=True) | Q(user_roles__expires_at__gt=now),
            user_roles__is_active=True,
            user_roles__role__is_active=True,
            user_roles__branch_id__in=tuple(branch_ids),
        )
        .distinct()
        .order_by("first_name", "last_name", "username")
    )
