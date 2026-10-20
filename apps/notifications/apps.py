"""ES: Este módulo configura la aplicación Django para el dominio de notificaciones.

EN: This module configures the Django application for the notifications domain.

Contexto existente / Existing context:
Django application configuration for the notifications domain.
"""

from django.apps import AppConfig

class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'
    verbose_name = 'Notificaciones'
