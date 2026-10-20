"""ES: Este módulo configura la aplicación Django para el dominio de facturación.

EN: This module configures the Django application for the invoices domain.

Contexto existente / Existing context:
Django application configuration for the invoices domain.
"""

from django.apps import AppConfig

class InvoicesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.invoices'
    verbose_name = 'Facturación'
