"""ES: Este módulo centraliza reglas de autorización para el dominio de ayuda.

EN: This module centralizes authorization rules for the help center domain.

Contexto existente / Existing context:
Authorization helpers for the help center domain.
"""

from django.core.exceptions import PermissionDenied


def require_help_access(user):
    if not user.is_authenticated or not user.can_view_help:
        raise PermissionDenied("No tienes acceso al centro de ayuda.")
