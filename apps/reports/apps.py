"""ES: Este módulo configura la aplicación Django para el dominio de reportes.

EN: This module configures the Django application for the reports domain.

Contexto existente / Existing context:
Django application configuration for the reports domain.
"""

from django.apps import AppConfig

class ReportsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.reports'
    verbose_name = 'Reportes'
