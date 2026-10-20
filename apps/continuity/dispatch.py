"""ES: Este módulo implementa el componente dispatch para el dominio de continuidad.

EN: This module implements the dispatch component for the continuity domain.

Contexto existente / Existing context:
Dispatch support for the continuity domain.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from django.conf import settings
from django.utils import timezone

from apps.audit.services import audit_log
from apps.continuity.models import BackupRecord
from apps.continuity.services import execute_backup, mark_backup_failed
from apps.continuity.tasks import run_backup_task

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BackupDispatchResult:
    record: BackupRecord
    queued: bool
    used_sync_fallback: bool
    message: str


def _safe_queue_error(exc: Exception) -> str:
    return f"{exc.__class__.__name__}: no se pudo publicar la tarea en el broker configurado."


def enqueue_backup(
    record: BackupRecord,
    *,
    allow_sync_fallback: bool | None = None,
    execution_mode: str = BackupRecord.ExecutionMode.ASYNC,
) -> BackupDispatchResult:
    """Publica un backup y aplica una política de fallback explícita y auditable."""

    if allow_sync_fallback is None:
        allow_sync_fallback = settings.VINOVA_BACKUP_SYNC_FALLBACK

    record.status = BackupRecord.Status.PENDING
    record.execution_mode = execution_mode
    record.queued_at = timezone.now()
    record.queue_error = ""
    record.error_message = ""
    record.save(
        update_fields=[
            "status",
            "execution_mode",
            "queued_at",
            "queue_error",
            "error_message",
            "updated_at",
        ]
    )

    retry_policy = {
        "max_retries": settings.VINOVA_BACKUP_PUBLISH_MAX_RETRIES,
        "interval_start": 0,
        "interval_step": 1,
        "interval_max": 3,
    }
    try:
        async_result = run_backup_task.apply_async(
            args=[record.pk],
            queue=settings.CELERY_BACKUP_QUEUE,
            retry=settings.VINOVA_BACKUP_PUBLISH_RETRY,
            retry_policy=retry_policy,
        )
    except Exception as exc:  # noqa: BLE001 - la indisponibilidad del broker no debe causar un 500
        safe_error = _safe_queue_error(exc)
        logger.exception("No se pudo encolar el backup %s", record.public_id)
        record.queue_error = safe_error
        record.save(update_fields=["queue_error", "updated_at"])
        audit_log(
            user=record.initiated_by,
            action="continuity.backup.queue_unavailable",
            target=record,
            after={"fallback_allowed": allow_sync_fallback, "error_type": exc.__class__.__name__},
            severity="high",
            result="failure",
        )

        if allow_sync_fallback:
            record.execution_mode = BackupRecord.ExecutionMode.SYNC_FALLBACK
            record.save(update_fields=["execution_mode", "updated_at"])
            execute_backup(record)
            record.refresh_from_db()
            return BackupDispatchResult(
                record=record,
                queued=False,
                used_sync_fallback=True,
                message="El broker no respondió; se aplicó el fallback síncrono configurado.",
            )

        mark_backup_failed(
            record,
            "No se pudo encolar el backup. Revise Redis, Celery Worker y la configuración del broker.",
        )
        record.refresh_from_db()
        return BackupDispatchResult(
            record=record,
            queued=False,
            used_sync_fallback=False,
            message="El backup no se ejecutó porque Celery no estaba disponible.",
        )

    record.celery_task_id = async_result.id or ""
    record.save(update_fields=["celery_task_id", "updated_at"])
    audit_log(
        user=record.initiated_by,
        action="continuity.backup.queued",
        target=record,
        after={"task_id": record.celery_task_id, "queue": settings.CELERY_BACKUP_QUEUE},
    )
    return BackupDispatchResult(
        record=record,
        queued=True,
        used_sync_fallback=False,
        message="Backup enviado a Celery.",
    )
