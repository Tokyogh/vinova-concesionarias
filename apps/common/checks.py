"""ES: Este módulo implementa el componente checks para el dominio de infraestructura compartida.

EN: This module implements the checks component for the common domain.

Contexto existente / Existing context:
Django system checks for the common domain.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.checks import Error, Warning, register


@register()
def vinova_operational_checks(app_configs, **kwargs):
    """ES: Ejecuta la operación «vinova operational checks» dentro del dominio de infraestructura compartida.

    EN: Executes the «vinova operational checks» operation within the common domain.
    """

    issues = []
    private_root = Path(settings.PRIVATE_STORAGE_ROOT).resolve()
    public_roots = {Path(settings.MEDIA_ROOT).resolve(), Path(settings.STATIC_ROOT).resolve()}
    if any(
        private_root == root or root in private_root.parents or private_root in root.parents for root in public_roots
    ):
        issues.append(
            Error(
                "PRIVATE_STORAGE_ROOT no puede estar dentro de media/ ni staticfiles/.",
                id="vinova.E001",
            )
        )
    if not settings.CELERY_BROKER_URL:
        issues.append(Error("CELERY_BROKER_URL no está configurado.", id="vinova.E002"))
    if not settings.CELERY_RESULT_BACKEND:
        issues.append(Error("CELERY_RESULT_BACKEND no está configurado.", id="vinova.E003"))
    bounded_settings = (
        "VINOVA_MAX_UPLOAD_MB",
        "VINOVA_ZIP_MAX_ENTRIES",
        "VINOVA_ZIP_MAX_UNCOMPRESSED_MB",
        "VINOVA_ZIP_MAX_COMPRESSION_RATIO",
        "VINOVA_IMPORT_MAX_ROWS",
        "VINOVA_IMPORT_MAX_COLUMNS",
        "VINOVA_ARCHIVE_MAX_MEMBERS",
        "VINOVA_ARCHIVE_MAX_UNCOMPRESSED_MB",
    )
    invalid_limits = [name for name in bounded_settings if getattr(settings, name, 0) < 1]
    if invalid_limits:
        issues.append(
            Error(
                "Los límites operativos deben ser enteros positivos: " + ", ".join(invalid_limits),
                id="vinova.E004",
            )
        )
    if not settings.DEBUG and settings.VINOVA_BACKUP_SYNC_FALLBACK:
        issues.append(
            Warning(
                "El fallback síncrono de backups está habilitado en producción.",
                hint="Configure VINOVA_BACKUP_SYNC_FALLBACK=False para no bloquear Gunicorn.",
                id="vinova.W001",
            )
        )
    if not settings.DEBUG and settings.VINOVA_API_DOCS_PUBLIC:
        issues.append(
            Warning(
                "Swagger/OpenAPI está expuesto públicamente en producción.",
                hint="Configure VINOVA_API_DOCS_PUBLIC=False.",
                id="vinova.W002",
            )
        )
    return issues
