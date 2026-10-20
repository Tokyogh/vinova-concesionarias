"""ES: Este módulo configura la aplicación Django para el dominio de portal cliente.

EN: This module configures the Django application for the portal domain.

Contexto existente / Existing context:
Django application configuration for the portal domain.
"""

from django.apps import AppConfig


class PortalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.portal"
    verbose_name = "Portal de clientes"
