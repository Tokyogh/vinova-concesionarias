"""ES: Este módulo configura la aplicación Django para el dominio de API e integraciones.

EN: This module configures the Django application for the api domain.

Contexto existente / Existing context:
Django application configuration for the api domain.
"""

from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.api"
    verbose_name = "API e integraciones"

    def ready(self):
        from apps.api import schema  # noqa: F401
        from apps.api import signals  # noqa: F401
