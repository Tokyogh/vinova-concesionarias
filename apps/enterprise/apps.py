"""ES: Este módulo configura la aplicación Django para el dominio de configuración empresarial.

EN: This module configures the Django application for the enterprise domain.

Contexto existente / Existing context:
Django application configuration for the enterprise domain.
"""

from django.apps import AppConfig


class EnterpriseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.enterprise"
    verbose_name = "Centro empresarial"
