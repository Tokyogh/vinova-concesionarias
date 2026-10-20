"""ES: Este módulo configura la aplicación Django para el dominio de privacidad.

EN: This module configures the Django application for the privacy domain.

Contexto existente / Existing context:
Django application configuration for the privacy domain.
"""

from django.apps import AppConfig


class PrivacyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.privacy"
    verbose_name = "Protección de datos"

    def ready(self):
        from apps.privacy import signals  # noqa: F401
