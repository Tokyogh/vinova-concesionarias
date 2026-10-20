"""ES: Este módulo expone tareas asíncronas y sus límites operativos para el dominio de infraestructura compartida.

EN: This module exposes asynchronous tasks and their operational limits for the common domain.

Contexto existente / Existing context:
Asynchronous task entry points for the common domain.
"""

from __future__ import annotations

import socket

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


@shared_task(name="apps.common.tasks.system_heartbeat", ignore_result=True)
def system_heartbeat() -> dict[str, object]:
    """Pulso no sensible que demuestra que Beat publicó y un Worker ejecutó."""

    payload = {
        "timestamp": timezone.now().timestamp(),
        "worker": socket.gethostname(),
        "version": settings.VINOVA_PRODUCT_VERSION,
    }
    cache.set(settings.VINOVA_CELERY_HEALTH_KEY, payload, timeout=settings.VINOVA_CELERY_HEARTBEAT_MAX_AGE * 2)
    return payload
