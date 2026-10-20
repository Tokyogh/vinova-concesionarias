"""ES: Este módulo configura la aplicación Django para el dominio de ventas.

EN: This module configures the Django application for the sales domain.

Contexto existente / Existing context:
Django application configuration for the sales domain.
"""

from django.apps import AppConfig


class SalesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sales"
    verbose_name = "Ventas y cotizaciones"
