#!/usr/bin/env python
"""ES: Este módulo implementa el componente wait for dependencies para el dominio de operación y QA.

EN: This module implements the wait for dependencies component for the operations and QA domain.

Contexto existente / Existing context:
Operational script for wait for dependencies.
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    os.getenv("DJANGO_SETTINGS_MODULE", "config.settings.production"),
)

import django  # noqa: E402

django.setup()

from django.core.cache import cache  # noqa: E402
from django.db import connections  # noqa: E402

URL_CREDENTIALS = re.compile(r"(?P<scheme>[a-z][a-z0-9+.-]*://)(?P<credentials>[^@\s]+)@", re.IGNORECASE)


def safe_error(exc: Exception) -> str:
    message = " ".join(str(exc).split())
    message = URL_CREDENTIALS.sub(r"\g<scheme>***@", message)
    return (message or exc.__class__.__name__)[:300]


def check_postgres() -> None:
    connection = connections["default"]
    connection.ensure_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        if cursor.fetchone() != (1,):
            raise RuntimeError("PostgreSQL no devolvio el valor esperado")


def check_redis() -> None:
    probe_key = "vinova:startup:probe"
    cache.set(probe_key, "ok", timeout=10)
    if cache.get(probe_key) != "ok":
        raise RuntimeError("Redis no devolvio el valor de prueba")


def main() -> int:
    timeout = int(os.getenv("VINOVA_WAIT_TIMEOUT", "120"))
    interval = max(1.0, float(os.getenv("VINOVA_WAIT_INTERVAL", "2")))
    deadline = time.monotonic() + timeout
    last_detail = ""
    attempts = 0

    while time.monotonic() < deadline:
        attempts += 1
        stage = "PostgreSQL"
        try:
            check_postgres()
            stage = "Redis"
            check_redis()
            print(f"Dependencias disponibles tras {attempts} intento(s): PostgreSQL y Redis.")
            return 0
        except Exception as exc:  # noqa: BLE001
            connections.close_all()
            detail = f"{stage}: {exc.__class__.__name__}: {safe_error(exc)}"
            if detail != last_detail or attempts == 1 or attempts % 10 == 0:
                print(f"Esperando dependencias ({detail})...", flush=True)
                last_detail = detail
            time.sleep(interval)

    print(
        f"Tiempo agotado esperando dependencias tras {attempts} intento(s). Ultimo error: {last_detail}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
