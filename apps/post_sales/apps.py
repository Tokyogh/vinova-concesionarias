"""ES: Este módulo configura la aplicación Django para el dominio de postventa.

EN: This module configures the Django application for the post sales domain.

Contexto existente / Existing context:
Django application configuration for the post sales domain.
"""

from django.apps import AppConfig


class PostSalesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.post_sales"
    verbose_name = "Postventa"
