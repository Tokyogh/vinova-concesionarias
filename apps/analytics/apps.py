"""ES: Este módulo configura la aplicación Django para el dominio de analítica.

EN: This module configures the Django application for the analytics domain.

Contexto existente / Existing context:
Django application configuration for the analytics domain.
"""

from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.analytics"
    verbose_name = "Analítica comercial"
