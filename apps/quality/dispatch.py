"""ES: Este módulo implementa el componente dispatch para el dominio de calidad.

EN: This module implements the dispatch component for the quality domain.

Contexto existente / Existing context:
Dispatch support for the quality domain.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from apps.audit.services import audit_log
from apps.quality.models import QualityRun
from apps.quality.services import mark_quality_run_error
from apps.quality.tasks import run_quality_profile_task


@dataclass(frozen=True)
class QualityDispatchResult:
    run: QualityRun
    queued: bool
    message: str


def enqueue_quality_run(run: QualityRun) -> QualityDispatchResult:
    if not settings.VINOVA_QA_EXECUTION_ENABLED:
        run = mark_quality_run_error(
            run,
            "El ejecutor QA está desactivado. Inicie el perfil Docker QA o habilite la configuración operativa.",
        )
        return QualityDispatchResult(
            run=run,
            queued=False,
            message="El ejecutor QA no está habilitado en este entorno.",
        )
    try:
        result = run_quality_profile_task.apply_async(args=[run.pk], queue=settings.CELERY_QA_QUEUE)
    except Exception as exc:  # noqa: BLE001 - un fallo del broker debe quedar registrado y saneado
        safe_message = f"{exc.__class__.__name__}: no se pudo publicar la validación en la cola QA."
        run = mark_quality_run_error(run, safe_message)
        audit_log(
            user=run.requested_by,
            action="quality.run.queue_failed",
            target=run,
            after={"profile": run.profile, "error_type": exc.__class__.__name__},
            severity="high",
            result="failure",
        )
        return QualityDispatchResult(run=run, queued=False, message="No se pudo contactar con la cola QA.")

    run.celery_task_id = result.id or ""
    run.save(update_fields=["celery_task_id", "updated_at"])
    audit_log(
        user=run.requested_by,
        action="quality.run.queued",
        target=run,
        after={"profile": run.profile, "task_id": run.celery_task_id, "queue": settings.CELERY_QA_QUEUE},
    )
    return QualityDispatchResult(run=run, queued=True, message="Validación enviada al QA Bot.")
