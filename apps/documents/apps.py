"""ES: Este módulo configura la aplicación Django para el dominio de documentos.

EN: This module configures the Django application for the documents domain.

Contexto existente / Existing context:
Django application configuration for the documents domain.
"""

from django.apps import AppConfig

class DocumentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.documents'
    verbose_name = 'Documentos'
