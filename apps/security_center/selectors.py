"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de seguridad.

EN: This module implements authorization-aware read queries for the security center domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the security center domain.
"""

from apps.accounts.models import User
from apps.accounts.scopes import accessible_branch_ids, accessible_users_queryset
from apps.security_center.models import ActiveSession, UserSecurityProfile


def security_users_queryset(*, user, permission_code="security.view"):
    branch_ids = accessible_branch_ids(user, permission_codes=(permission_code,))
    if branch_ids is None:
        return User.objects.all().order_by("username")
    return accessible_users_queryset(
        user,
        permission_codes=(permission_code,),
        active_only=False,
    ).order_by("username")


def security_profiles_queryset(*, user, permission_code="security.view"):
    user_ids = security_users_queryset(user=user, permission_code=permission_code).values("pk")
    return UserSecurityProfile.objects.filter(user_id__in=user_ids).select_related("user")


def active_sessions_queryset(*, user, permission_code="security.view"):
    user_ids = security_users_queryset(user=user, permission_code=permission_code).values("pk")
    return ActiveSession.objects.filter(user_id__in=user_ids).select_related("user")
