"""ES: Este módulo configura la aplicación Django para el dominio de importaciones.

EN: This module configures the Django application for the imports domain.

Contexto existente / Existing context:
Django application configuration for the imports domain.
"""

from django.apps import AppConfig


class ImportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.imports"
    verbose_name = "Importaciones masivas"
