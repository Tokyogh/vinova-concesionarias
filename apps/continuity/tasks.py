"""ES: Este módulo expone tareas asíncronas y sus límites operativos para el dominio de continuidad.

EN: This module exposes asynchronous tasks and their operational limits for the continuity domain.

Contexto existente / Existing context:
Asynchronous task entry points for the continuity domain.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.continuity.models import BackupPolicy, BackupRecord
from apps.continuity.services import create_backup_record, execute_backup

logger = logging.getLogger(__name__)

_RETRYABLE_MARKERS = (
    "timeout",
    "temporarily unavailable",
    "connection refused",
    "could not connect",
    "connection reset",
)


@shared_task(
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=1,
    default_retry_delay=60,
)
def run_backup_task(self, backup_id: int):
    record = BackupRecord.objects.get(pk=backup_id)
    record = execute_backup(record)
    if record.status == BackupRecord.Status.FAILED:
        message = (record.error_message or "backup failed").lower()
        retryable = any(marker in message for marker in _RETRYABLE_MARKERS)
        if retryable and self.request.retries < self.max_retries:
            logger.warning("Reintentando backup %s por error transitorio", record.public_id)
            raise self.retry(exc=RuntimeError("Error transitorio durante el backup; consulte el registro."))
        raise RuntimeError(f"El backup {record.public_id} falló; consulte el historial de continuidad.")
    return str(record.public_id)


def _policy_due(policy: BackupPolicy, now) -> bool:
    if policy.frequency == BackupPolicy.Frequency.MANUAL:
        return False
    if not policy.last_success_at:
        return True
    elapsed = now - policy.last_success_at
    thresholds = {
        BackupPolicy.Frequency.DAILY: timedelta(days=1),
        BackupPolicy.Frequency.WEEKLY: timedelta(days=7),
        BackupPolicy.Frequency.MONTHLY: timedelta(days=30),
    }
    return elapsed >= thresholds.get(policy.frequency, timedelta(days=1))


@shared_task(name="apps.continuity.tasks.schedule_policy_backups", ignore_result=True)
def schedule_policy_backups() -> dict[str, object]:
    """Evalúa la política sin crear backups salvo activación explícita por entorno."""

    if not settings.VINOVA_AUTOMATED_BACKUPS_ENABLED:
        return {"enabled": False, "scheduled": False}

    lock_key = "vinova:continuity:policy-scheduler-lock"
    if not cache.add(lock_key, timezone.now().timestamp(), timeout=240):
        return {"enabled": True, "scheduled": False, "reason": "locked"}

    try:
        policy = BackupPolicy.objects.filter(is_active=True).order_by("created_at").first()
        if not policy or not _policy_due(policy, timezone.now()):
            return {"enabled": True, "scheduled": False, "reason": "not_due"}

        active = BackupRecord.objects.filter(
            policy=policy,
            status__in=[BackupRecord.Status.PENDING, BackupRecord.Status.RUNNING],
        ).exists()
        if active:
            return {"enabled": True, "scheduled": False, "reason": "already_active"}

        backup_type = BackupRecord.BackupType.FULL
        if policy.include_database and not (policy.include_media or policy.include_private):
            backup_type = BackupRecord.BackupType.DATABASE
        elif not policy.include_database and (policy.include_media or policy.include_private):
            backup_type = BackupRecord.BackupType.FILES

        record = create_backup_record(
            actor=None,
            backup_type=backup_type,
            notes=f"Backup automático por política: {policy.name}",
            execution_mode=BackupRecord.ExecutionMode.SCHEDULED,
        )
        from apps.continuity.dispatch import enqueue_backup

        result = enqueue_backup(
            record,
            allow_sync_fallback=False,
            execution_mode=BackupRecord.ExecutionMode.SCHEDULED,
        )
        return {
            "enabled": True,
            "scheduled": result.queued,
            "backup_id": str(record.public_id),
        }
    finally:
        cache.delete(lock_key)
