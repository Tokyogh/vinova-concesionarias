"""ES: Este módulo centraliza reglas de autorización para el dominio de reportes.

EN: This module centralizes authorization rules for the reports domain.

Contexto existente / Existing context:
Authorization helpers for the reports domain.
"""

from rest_framework.permissions import BasePermission


class CanViewReports(BasePermission):
    message = "No tienes permiso para ver reportes empresariales."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_superuser or user.can_view_reports))
