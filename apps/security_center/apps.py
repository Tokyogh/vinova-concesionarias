"""ES: Este módulo configura la aplicación Django para el dominio de seguridad.

EN: This module configures the Django application for the security center domain.

Contexto existente / Existing context:
Django application configuration for the security center domain.
"""

from django.apps import AppConfig


class SecurityCenterConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.security_center"
    verbose_name = "Seguridad y hardening"

    def ready(self):
        from apps.security_center import checks, signals  # noqa: F401
