"""ES: Este módulo implementa el componente context processors para el dominio de ayuda.

EN: This module implements the context processors component for the help center domain.

Contexto existente / Existing context:
Template context providers for the help center domain.
"""

from __future__ import annotations

from apps.help_center.selectors import contextual_article_for_user, training_mode_for_user


def help_center_context(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or not user.can_view_help:
        return {"help_training_mode": False, "contextual_help_article": None}
    resolver_match = getattr(request, "resolver_match", None)
    route_name = resolver_match.view_name if resolver_match else ""
    return {
        "help_training_mode": training_mode_for_user(user),
        "contextual_help_article": contextual_article_for_user(user, route_name),
    }
