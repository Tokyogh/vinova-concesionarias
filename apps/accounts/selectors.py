"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de cuentas.

EN: This module implements authorization-aware read queries for the accounts domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the accounts domain.
"""

from __future__ import annotations

from django.db.models import Count, Prefetch, Q, QuerySet

from apps.accounts.models import Role, User, UserRole
from apps.accounts.scopes import accessible_management_branch_ids


def manageable_users_queryset(user, *, active_only: bool = False) -> QuerySet[User]:
    """Users the actor can manage in the HTML backend.

    Global actors (any role assignment with the management permission without a
    branch) keep full reach. Branch-bound actors only see users tied to their
    accessible branches: through an active role assignment in those branches or
    through their optional main branch.
    """
    branch_ids = accessible_management_branch_ids(user)
    if branch_ids is None:
        return User.objects.all().order_by("username")
    if not branch_ids:
        return User.objects.none()
    qs = User.objects.filter(
        Q(branch_id__in=branch_ids)
        | Q(user_roles__is_active=True, user_roles__role__is_active=True, user_roles__branch_id__in=branch_ids)
    )
    if active_only:
        qs = qs.filter(is_active=True)
    return qs.distinct().order_by("username")


def user_list_queryset(user, *, query: str = "") -> QuerySet[User]:
    qs = (
        manageable_users_queryset(user)
        .select_related("branch")
        .prefetch_related(
            Prefetch(
                "user_roles",
                queryset=UserRole.objects.filter(is_active=True).select_related("role", "branch"),
                to_attr="active_user_roles",
            )
        )
        .annotate(active_roles_count=Count("user_roles", filter=Q(user_roles__is_active=True), distinct=True))
    )
    if query:
        qs = qs.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(phone__icontains=query)
        )
    return qs


def user_detail_queryset(user) -> QuerySet[User]:
    return manageable_users_queryset(user).select_related("branch").prefetch_related("user_roles__role", "user_roles__branch")


def active_roles_queryset() -> QuerySet[Role]:
    return Role.objects.filter(is_active=True).prefetch_related("permissions").order_by("level", "name")


def active_user_roles_for(user: User) -> QuerySet[UserRole]:
    return user.user_roles.filter(is_active=True).select_related("role", "branch").order_by("role__level", "role__name")


def visible_user_roles_for(actor: User, target_user: User) -> list[UserRole]:
    """Active role bindings of target_user the actor may manage and see.

    Only bindings within the actor's real authority are returned, so a
    branch-bound manager does not leak global or more privileged assignments.
    """
    from apps.accounts.scopes import role_binding_in_authority

    qs = active_user_roles_for(target_user)
    if getattr(actor, "is_superuser", False):
        return list(qs)
    return [binding for binding in qs if role_binding_in_authority(actor=actor, role=binding.role, branch=binding.branch)]
