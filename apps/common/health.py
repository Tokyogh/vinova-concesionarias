"""ES: Este módulo implementa el componente health para el dominio de infraestructura compartida.

EN: This module implements the health component for the common domain.

Contexto existente / Existing context:
Health support for the common domain.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from time import time

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.db import connections
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


def _database_check() -> tuple[bool, str]:
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True, "ok"
    except Exception as exc:  # noqa: BLE001 - healthcheck operacional
        return False, exc.__class__.__name__


def _redis_check() -> tuple[bool, str]:
    try:
        key = "vinova:health:readiness"
        marker = f"{time():.6f}"
        cache.set(key, marker, timeout=15)
        cached_marker = cache.get(key)
        matches = cached_marker == marker
        return matches, "ok" if matches else "cache_mismatch"
    except Exception as exc:  # noqa: BLE001
        return False, exc.__class__.__name__


def _storage_check() -> tuple[bool, str]:
    if settings.PRIVATE_STORAGE_BACKEND != "local":
        from apps.documents.storage import private_storage_health_check

        return private_storage_health_check()
    try:
        root = Path(settings.PRIVATE_STORAGE_ROOT)
        root.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix=".vinova-health-", dir=root)
        os.close(descriptor)
        Path(name).unlink(missing_ok=True)
        return True, "ok"
    except Exception as exc:  # noqa: BLE001
        return False, exc.__class__.__name__


def _celery_pipeline_check() -> tuple[bool, str]:
    try:
        payload = cache.get(settings.VINOVA_CELERY_HEALTH_KEY)
    except Exception as exc:  # noqa: BLE001
        return False, exc.__class__.__name__
    if not isinstance(payload, dict) or "timestamp" not in payload:
        return False, "missing_heartbeat"
    age = max(0.0, time() - float(payload["timestamp"]))
    if age > settings.VINOVA_CELERY_HEARTBEAT_MAX_AGE:
        return False, "stale_heartbeat"
    return True, "ok"


def dependency_status() -> dict[str, tuple[bool, str]]:
    status = {
        "database": _database_check(),
        "redis": _redis_check(),
        "storage": _storage_check(),
    }
    if settings.STORAGE_BACKEND != "local":
        from apps.accounts.storage import avatar_storage_health_check

        status["avatar_storage"] = avatar_storage_health_check()
    if settings.VINOVA_REQUIRE_CELERY_READY:
        status["celery_pipeline"] = _celery_pipeline_check()
    return status


@never_cache
@require_GET
def live(request):
    return JsonResponse({"status": "ok", "service": "vinova-pro"})


@never_cache
@require_GET
def ready(request):
    checks = dependency_status()
    available = all(ok for ok, _ in checks.values())
    response = {"status": "ready" if available else "unavailable"}
    return JsonResponse(response, status=200 if available else 503)


@never_cache
@require_GET
@staff_member_required
def dependencies(request):
    checks = dependency_status()
    available = all(ok for ok, _ in checks.values())
    return JsonResponse(
        {
            "status": "ready" if available else "unavailable",
            "checks": {name: {"ok": ok, "detail": detail} for name, (ok, detail) in checks.items()},
        },
        status=200 if available else 503,
    )
