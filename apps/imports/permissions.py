"""ES: Este módulo centraliza reglas de autorización para el dominio de importaciones.

EN: This module centralizes authorization rules for the imports domain.

Contexto existente / Existing context:
Authorization helpers for the imports domain.
"""

from rest_framework.permissions import BasePermission


class CanManageImports(BasePermission):
    message = "No tienes permiso para gestionar importaciones masivas."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_superuser or getattr(user, "can_manage_imports", False)))
