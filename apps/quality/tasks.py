"""ES: Este módulo expone tareas asíncronas y sus límites operativos para el dominio de calidad.

EN: This module exposes asynchronous tasks and their operational limits for the quality domain.

Contexto existente / Existing context:
Asynchronous task entry points for the quality domain.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.audit.services import audit_log
from apps.quality.models import QualityRun
from apps.quality.runner import run_quality_profile
from apps.quality.services import (
    apply_quality_report,
    cleanup_expired_quality_evidence,
    create_quality_run,
    mark_quality_run_error,
    mark_quality_run_running,
)

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="apps.quality.tasks.run_quality_profile_task",
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=0,
)
def run_quality_profile_task(self, run_id: int) -> dict[str, object]:
    run = QualityRun.objects.select_related("requested_by").get(pk=run_id)
    if not settings.VINOVA_QA_EXECUTION_ENABLED:
        mark_quality_run_error(run, "La ejecución QA está deshabilitada en este entorno.")
        return {"run_id": str(run.public_id), "status": "disabled"}

    run = mark_quality_run_running(run, task_id=self.request.id or "")
    audit_log(
        user=run.requested_by,
        action="quality.run.started",
        target=run,
        after={"profile": run.profile, "environment": settings.VINOVA_QA_ENVIRONMENT},
    )
    try:
        report = run_quality_profile(
            profile=run.profile,
            root=settings.BASE_DIR,
            report_dir=settings.VINOVA_QA_REPORT_ROOT,
            run_id=str(run.public_id),
            require_postgres=run.profile == QualityRun.Profile.RELEASE,
        )
        run = apply_quality_report(run, report)
    except Exception as exc:  # noqa: BLE001 - se registra sin exponer credenciales o salida completa
        logger.exception("La ejecución QA %s terminó con error operativo", run.public_id)
        run = mark_quality_run_error(run, f"{exc.__class__.__name__}: {exc}")

    audit_log(
        user=run.requested_by,
        action="quality.run.completed",
        target=run,
        after={
            "profile": run.profile,
            "status": run.status,
            "passed": run.passed_count,
            "warnings": run.warning_count,
            "failed": run.failed_count,
        },
        severity="high" if run.status in {QualityRun.Status.FAILED, QualityRun.Status.ERROR} else "info",
        result="failure" if run.status in {QualityRun.Status.FAILED, QualityRun.Status.ERROR} else "success",
    )
    return {"run_id": str(run.public_id), "status": run.status, "release_ready": run.release_ready}


@shared_task(name="apps.quality.tasks.schedule_automated_quality_run", ignore_result=True)
def schedule_automated_quality_run() -> dict[str, object]:
    if not settings.VINOVA_QA_AUTOMATED_ENABLED or not settings.VINOVA_QA_EXECUTION_ENABLED:
        return {"enabled": False, "scheduled": False}
    recent_cutoff = timezone.now() - timedelta(hours=settings.VINOVA_QA_AUTOMATED_MIN_INTERVAL_HOURS)
    if QualityRun.objects.filter(created_at__gte=recent_cutoff, trigger=QualityRun.Trigger.SCHEDULED).exists():
        return {"enabled": True, "scheduled": False, "reason": "recent_run"}
    try:
        run = create_quality_run(
            profile=QualityRun.Profile.QUICK,
            trigger=QualityRun.Trigger.SCHEDULED,
            actor=None,
        )
    except ValueError:
        return {"enabled": True, "scheduled": False, "reason": "active_run"}
    from apps.quality.dispatch import enqueue_quality_run

    result = enqueue_quality_run(run)
    return {"enabled": True, "scheduled": result.queued, "run_id": str(run.public_id)}


@shared_task(name="apps.quality.tasks.cleanup_quality_evidence_task", ignore_result=True)
def cleanup_quality_evidence_task() -> dict[str, object]:
    purged = cleanup_expired_quality_evidence()
    return {"purged_runs": purged, "retention_days": settings.VINOVA_QA_RETENTION_DAYS}
