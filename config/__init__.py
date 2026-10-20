"""ES: Este módulo implementa el componente   init   para el dominio de configuración.

EN: This module implements the   init   component for the configuration domain.

Contexto existente / Existing context:
Configuración principal de Vinova Pro.

Importar la aplicación Celery aquí es imprescindible: los procesos Django (web,
management commands y ASGI/WSGI) deben compartir la misma instancia y broker que
los workers. Sin esta importación, ``shared_task.delay()`` puede quedar enlazado a
la aplicación Celery por defecto y tratar de usar un broker distinto.
"""

from config.celery import app as celery_app

__all__ = ("celery_app",)
