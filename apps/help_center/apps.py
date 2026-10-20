"""ES: Este módulo configura la aplicación Django para el dominio de ayuda.

EN: This module configures the Django application for the help center domain.

Contexto existente / Existing context:
Django application configuration for the help center domain.
"""

from django.apps import AppConfig


class HelpCenterConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.help_center"
    verbose_name = "Ayuda y capacitación"
