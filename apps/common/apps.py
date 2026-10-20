"""ES: Este módulo configura la aplicación Django para el dominio de infraestructura compartida.

EN: This module configures the Django application for the common domain.

Contexto existente / Existing context:
Django application configuration for the common domain.
"""

from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"
    verbose_name = "Base común"

    def ready(self):
        from apps.common import checks  # noqa: F401
