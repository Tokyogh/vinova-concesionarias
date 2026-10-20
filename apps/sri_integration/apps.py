"""ES: Este módulo configura la aplicación Django para el dominio de configuración SRI heredada.

EN: This module configures the Django application for the sri integration domain.

Contexto existente / Existing context:
Django application configuration for the sri integration domain.
"""

from django.apps import AppConfig


class SriIntegrationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sri_integration"
    verbose_name = "Integración SRI base"
