"""ES: Este módulo implementa el componente celery para el dominio de configuración.

EN: This module implements the celery component for the configuration domain.

Contexto existente / Existing context:
Vinova runtime configuration for celery.
"""

from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    os.getenv("DJANGO_SETTINGS_MODULE", "config.settings.production"),
)

app = Celery("vinova_pro")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
