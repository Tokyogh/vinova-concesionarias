"""ES: Este módulo configura la aplicación Django para el dominio de paneles.

EN: This module configures the Django application for the dashboard domain.

Contexto existente / Existing context:
Django application configuration for the dashboard domain.
"""

from django.apps import AppConfig

class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dashboard'
    verbose_name = 'Dashboard'
