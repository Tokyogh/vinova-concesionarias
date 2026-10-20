"""ES: Este módulo implementa el componente qa safety para el dominio de cuentas.

EN: This module implements the qa safety component for the accounts domain.

Contexto existente / Existing context:
Qa safety support for the accounts domain.
"""

from __future__ import annotations

import os

from django.conf import settings
from django.core.management.base import CommandError


def assert_non_production_database() -> None:
    """Block QA data commands outside explicitly safe environments."""
    environment = os.getenv("VINOVA_ENVIRONMENT", "").strip().lower()
    if environment in {"prod", "production"}:
        raise CommandError("Este comando está prohibido en producción.")

    local_environments = {"local", "development", "dev", "demo", "test"}
    allowed_environments = local_environments | {"staging"}
    host = (settings.DATABASES["default"].get("HOST") or "").strip().lower()
    local_host = host in {"", "localhost", "127.0.0.1", "::1", "db", "postgres", "qa_db"}
    environment_is_unset_local = not environment and settings.DEBUG and local_host
    if environment not in allowed_environments and not environment_is_unset_local:
        raise CommandError(
            "Define VINOVA_ENVIRONMENT como local/development/staging/test antes de provisionar QA."
        )
    if environment != "staging" and not local_host:
        raise CommandError("La base de datos no parece local; se cancela para proteger datos reales.")
