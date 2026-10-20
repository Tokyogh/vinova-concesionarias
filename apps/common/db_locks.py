"""ES: Este módulo implementa el componente db locks para el dominio de infraestructura compartida.

EN: This module implements the db locks component for the common domain.

Contexto existente / Existing context:
Db locks support for the common domain.
"""

from __future__ import annotations

from django.db import connection


def acquire_transaction_advisory_lock(*, namespace: str, value: str) -> None:
    """Serialize a logical resource for the current PostgreSQL transaction."""
    if connection.vendor != "postgresql":
        return
    lock_name = f"vinova:{namespace}:{value}"
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", [lock_name])
