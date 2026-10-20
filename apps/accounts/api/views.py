"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de cuentas.

EN: This module orchestrates HTTP requests, permissions, and responses for the accounts domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the accounts domain.
"""

from __future__ import annotations

from django.db.models import Prefetch
from rest_framework.permissions import BasePermission
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.accounts.api.serializers import ACTIVE_API_ROLES_ATTR, RoleSerializer, UserSerializer
from apps.accounts.models import Role, User, UserRole
from apps.accounts.scopes import accessible_branch_ids, has_global_permission, users_in_branches_queryset


class AccountUserPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.has_perm_code("accounts.manage_users")
        )


class GlobalRolePermission(BasePermission):
    def has_permission(self, request, view):
        return has_global_permission(request.user, "accounts.assign_roles")


class UserViewSet(ReadOnlyModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [AccountUserPermission]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering_fields = ["username", "email", "first_name", "last_name", "is_active", "date_joined"]
    ordering = ["username"]
    queryset = User.objects.none()

    def get_queryset(self):
        api_client = getattr(self.request, "api_client", None)
        branch_ids = (
            (api_client.branch_id,)
            if api_client and api_client.branch_id
            else accessible_branch_ids(self.request.user, permission_codes=("accounts.manage_users",))
        )
        users = (
            User.objects.all()
            if branch_ids is None
            else users_in_branches_queryset(branch_ids, active_only=False)
        )
        role_assignments = UserRole.objects.filter(is_active=True, role__is_active=True)
        if branch_ids is not None:
            role_assignments = role_assignments.filter(branch_id__in=branch_ids)
        return users.select_related("branch").prefetch_related(
            Prefetch(
                "user_roles",
                queryset=role_assignments.select_related("role", "branch"),
                to_attr=ACTIVE_API_ROLES_ATTR,
            )
        )


class RoleViewSet(ReadOnlyModelViewSet):
    serializer_class = RoleSerializer
    permission_classes = [GlobalRolePermission]
    queryset = Role.objects.all()
    search_fields = ["code", "name"]
    ordering_fields = ["level", "name", "code", "is_active"]
    ordering = ["level", "name"]
