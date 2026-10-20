"""ES: Este módulo configura la aplicación Django para el dominio de auditoría.

EN: This module configures the Django application for the audit domain.

Contexto existente / Existing context:
Django application configuration for the audit domain.
"""

from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    verbose_name = "Auditoría"

    def ready(self):
        from apps.audit import signals  # noqa: F401
