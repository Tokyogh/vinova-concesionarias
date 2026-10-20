"""ES: Este módulo configura la aplicación Django para el dominio de continuidad.

EN: This module configures the Django application for the continuity domain.

Contexto existente / Existing context:
Django application configuration for the continuity domain.
"""

from django.apps import AppConfig


class ContinuityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.continuity"
    verbose_name = "Continuidad y recuperación"
