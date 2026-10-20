"""ES: Este módulo configura la aplicación Django para el dominio de sucursales.

EN: This module configures the Django application for the branches domain.

Contexto existente / Existing context:
Django application configuration for the branches domain.
"""

from django.apps import AppConfig

class BranchesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.branches'
    verbose_name = 'Sucursales'
