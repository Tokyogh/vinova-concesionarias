"""ES: Este módulo centraliza reglas de autorización para el dominio de calidad.

EN: This module centralizes authorization rules for the quality domain.

Contexto existente / Existing context:
Authorization helpers for the quality domain.
"""

from rest_framework.permissions import BasePermission

from apps.accounts.scopes import has_global_permission


def can_view_quality(user) -> bool:
    return bool(
        user
        and user.is_authenticated
        and (has_global_permission(user, "quality.view") or has_global_permission(user, "quality.run"))
    )


def can_run_quality(user) -> bool:
    return bool(user and user.is_authenticated and has_global_permission(user, "quality.run"))


class CanViewQuality(BasePermission):
    def has_permission(self, request, view):
        return can_view_quality(request.user)


class SessionQualityRunnerOnly(BasePermission):
    """QA nunca se dispara con clientes API de servicio ni comandos arbitrarios."""

    def has_permission(self, request, view):
        return not getattr(request, "api_client", None) and can_run_quality(request.user)
