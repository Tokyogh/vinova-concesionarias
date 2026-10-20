"""ES: Este módulo configura la aplicación Django para el dominio de clientes.

EN: This module configures the Django application for the customers domain.

Contexto existente / Existing context:
Django application configuration for the customers domain.
"""

from django.apps import AppConfig

class CustomersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.customers'
    verbose_name = 'Clientes'
