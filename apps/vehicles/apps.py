"""ES: Este módulo configura la aplicación Django para el dominio de vehículos.

EN: This module configures the Django application for the vehicles domain.

Contexto existente / Existing context:
Django application configuration for the vehicles domain.
"""

from django.apps import AppConfig

class VehiclesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.vehicles'
    verbose_name = 'Vehículos'
