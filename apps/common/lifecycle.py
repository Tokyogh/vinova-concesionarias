"""ES: Este módulo implementa el componente lifecycle para el dominio de infraestructura compartida.

EN: This module implements the lifecycle component for the common domain.

Contexto existente / Existing context:
Lifecycle support for the common domain.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from django.conf import settings
from django.db import connections
from django.db.migrations.executor import MigrationExecutor


VERSION_PATTERN = re.compile(r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$")


@dataclass(frozen=True, order=True)
class ProductVersion:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> "ProductVersion":
        match = VERSION_PATTERN.fullmatch((value or "").strip())
        if not match:
            raise ValueError("La versión debe usar SemVer estable MAJOR.MINOR.PATCH.")
        return cls(*(int(match.group(part)) for part in ("major", "minor", "patch")))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def assess_product_upgrade(
    current: str,
    target: str,
    *,
    migration_path_available: bool,
    release_compatible: bool,
) -> dict:
    """Evalúa política; no infiere compatibilidad sólo por comparar versiones."""
    try:
        current_version = ProductVersion.parse(current)
        target_version = ProductVersion.parse(target)
    except ValueError as exc:
        return {
            "allowed": False,
            "direction": "invalid",
            "requires_backup": True,
            "downgrade_supported": False,
            "reason": str(exc),
        }

    if target_version < current_version:
        return {
            "allowed": False,
            "direction": "downgrade",
            "requires_backup": True,
            "downgrade_supported": False,
            "reason": "El downgrade no está soportado; use un restore verificado de la versión anterior.",
        }
    if target_version == current_version:
        return {
            "allowed": True,
            "direction": "same",
            "requires_backup": False,
            "downgrade_supported": False,
            "reason": "La instalación ya usa la versión solicitada.",
        }
    if not release_compatible:
        return {
            "allowed": False,
            "direction": "upgrade",
            "requires_backup": True,
            "downgrade_supported": False,
            "reason": "El release no declara compatibilidad con esta instalación.",
        }
    if not migration_path_available:
        return {
            "allowed": False,
            "direction": "upgrade",
            "requires_backup": True,
            "downgrade_supported": False,
            "reason": "No existe una ruta de migración verificada hasta la versión objetivo.",
        }
    return {
        "allowed": True,
        "direction": "upgrade",
        "requires_backup": True,
        "downgrade_supported": False,
        "reason": "Upgrade forward permitido; requiere preflight y backup verificado.",
    }


def database_migration_state(*, using: str = "default") -> dict:
    """Describe el ledger Django; no pretende sustituir una inspección física del schema."""
    executor = MigrationExecutor(connections[using])
    targets = executor.loader.graph.leaf_nodes()
    plan = executor.migration_plan(targets)
    applied = sorted(f"{app}.{name}" for app, name in executor.loader.applied_migrations)
    pending = [f"{migration.app_label}.{migration.name}" for migration, backwards in plan if not backwards]
    fingerprint = hashlib.sha256("\n".join(applied).encode("utf-8")).hexdigest()
    return {
        "kind": "django-migration-ledger",
        "using": using,
        "is_current": not pending,
        "applied_count": len(applied),
        "pending_count": len(pending),
        "pending": pending,
        "leaf_nodes": [f"{app}.{name}" for app, name in sorted(targets)],
        "fingerprint_sha256": fingerprint,
    }


def installation_lifecycle_state(*, using: str = "default") -> dict:
    return {
        "product_version": settings.VINOVA_PRODUCT_VERSION,
        "database_migration_state": database_migration_state(using=using),
        "backup_format_version": settings.VINOVA_BACKUP_FORMAT_VERSION,
        "transfer_format_version": settings.VINOVA_TRANSFER_FORMAT_VERSION,
        "upgrade_policy": "forward-migrations-with-preflight-and-verified-backup",
        "downgrade_policy": "unsupported-use-verified-restore",
    }
