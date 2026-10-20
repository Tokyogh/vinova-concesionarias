"""ES: Este módulo configura la aplicación Django para el dominio de inventario.

EN: This module configures the Django application for the inventory domain.

Contexto existente / Existing context:
Django application configuration for the inventory domain.
"""

from django.apps import AppConfig

class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.inventory'
    verbose_name = 'Inventario'
