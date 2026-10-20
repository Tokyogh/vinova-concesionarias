"""ES: Este módulo centraliza reglas de autorización para el dominio de API e integraciones.

EN: This module centralizes authorization rules for the api domain.

Contexto existente / Existing context:
Authorization helpers for the api domain.
"""

from rest_framework.permissions import BasePermission


class CanViewIntegrations(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_superuser or user.has_perm_code("integrations.view") or user.has_perm_code("integrations.manage")))


class CanManageIntegrations(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_superuser or user.has_perm_code("integrations.manage")))


class SessionIntegrationAdminOnly(CanManageIntegrations):
    def has_permission(self, request, view):
        return not getattr(request, "api_client", None) and super().has_permission(request, view)
