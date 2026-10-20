"""ES: Este módulo configura la aplicación Django para el dominio de cuentas.

EN: This module configures the Django application for the accounts domain.

Contexto existente / Existing context:
Django application configuration for the accounts domain.
"""

from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = 'Cuentas y permisos'
