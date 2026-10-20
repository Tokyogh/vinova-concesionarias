"""ES: Este módulo configura la aplicación Django para el dominio de calidad.

EN: This module configures the Django application for the quality domain.

Contexto existente / Existing context:
Django application configuration for the quality domain.
"""

from django.apps import AppConfig


class QualityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.quality"
    verbose_name = "Calidad y preparación de release"
