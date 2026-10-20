"""ES: Este módulo configura la aplicación Django para el dominio de CRM y leads.

EN: This module configures the Django application for the leads domain.

Contexto existente / Existing context:
Django application configuration for the leads domain.
"""

from django.apps import AppConfig


class LeadsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.leads"
    verbose_name = "CRM y leads"
