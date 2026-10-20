"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de calidad.

EN: This module implements business services and transactional effects for the quality domain.

Contexto existente / Existing context:
Transactional business services for the quality domain.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.quality.models import QualityCheckResult, QualityRun

ACTIVE_STATUSES = {QualityRun.Status.QUEUED, QualityRun.Status.RUNNING}
QUALITY_RUN_CREATE_LOCK_KEY = "vinova:quality:create-run"


@transaction.atomic
def expire_stale_quality_runs(*, now=None) -> int:
    now = now or timezone.now()
    cutoff = now - timezone.timedelta(minutes=settings.VINOVA_QA_STALE_AFTER_MINUTES)
    stale = QualityRun.objects.select_for_update().filter(
        Q(status=QualityRun.Status.QUEUED, created_at__lt=cutoff)
        | Q(status=QualityRun.Status.RUNNING, started_at__lt=cutoff)
    )
    return stale.update(
        status=QualityRun.Status.ERROR,
        completed_at=now,
        failed_count=1,
        error_message="La ejecución excedió el tiempo operativo permitido y fue cerrada automáticamente.",
        updated_at=now,
    )


def _safe_report_relative_path(value: str) -> str:
    if not value:
        return ""
    root = Path(settings.VINOVA_QA_REPORT_ROOT).resolve()
    raw_candidate = Path(value)
    candidate = raw_candidate.resolve() if raw_candidate.is_absolute() else (root / raw_candidate).resolve()
    try:
        return candidate.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError("El reporte QA quedó fuera del almacenamiento privado autorizado.") from exc


def create_quality_run(*, profile: str, trigger: str, actor=None) -> QualityRun:
    if profile not in QualityRun.Profile.values:
        raise ValueError("Perfil QA no permitido.")
    try:
        acquired = cache.add(QUALITY_RUN_CREATE_LOCK_KEY, "locked", timeout=30)
    except Exception as exc:  # noqa: BLE001 - Redis puede estar temporalmente indisponible
        raise ValueError("No se pudo reservar el ejecutor QA; verifica Redis e inténtalo nuevamente.") from exc
    if not acquired:
        raise ValueError("Otra solicitud QA se está procesando; inténtalo nuevamente en unos segundos.")
    try:
        with transaction.atomic():
            expire_stale_quality_runs()
            active = QualityRun.objects.select_for_update().filter(status__in=ACTIVE_STATUSES).count()
            if active >= settings.VINOVA_QA_MAX_CONCURRENT_RUNS:
                raise ValueError("Ya existe una validación QA activa. Espera a que termine antes de iniciar otra.")
            return QualityRun.objects.create(
                profile=profile,
                trigger=trigger,
                requested_by=actor if getattr(actor, "is_authenticated", False) else None,
                source_version=settings.VINOVA_PRODUCT_VERSION,
                environment_name=settings.VINOVA_QA_ENVIRONMENT,
            )
    finally:
        try:
            cache.delete(QUALITY_RUN_CREATE_LOCK_KEY)
        except Exception:  # noqa: BLE001 - el lock expira por sí solo y no debe ocultar el resultado
            pass


@transaction.atomic
def mark_quality_run_running(run: QualityRun, *, task_id: str = "") -> QualityRun:
    run = QualityRun.objects.select_for_update().get(pk=run.pk)
    if run.status not in ACTIVE_STATUSES:
        raise ValueError("La ejecución QA ya no puede iniciarse.")
    run.status = QualityRun.Status.RUNNING
    run.started_at = run.started_at or timezone.now()
    if task_id:
        run.celery_task_id = task_id
    run.error_message = ""
    run.save(update_fields=["status", "started_at", "celery_task_id", "error_message", "updated_at"])
    return run


@transaction.atomic
def apply_quality_report(run: QualityRun, report: dict[str, Any]) -> QualityRun:
    """ES: Ejecuta la operación «apply quality report» dentro del dominio de calidad. Además, conserva atomicidad y bloqueos explícitos.

    EN: Executes the «apply quality report» operation within the quality domain. It also preserves atomicity and explicit locking.
    """

    run = QualityRun.objects.select_for_update().get(pk=run.pk)
    if str(run.public_id) != str(report.get("run_id")):
        raise ValueError("El identificador del reporte no coincide con la ejecución registrada.")
    if report.get("schema_version") != 1:
        raise ValueError("Versión de reporte QA no compatible.")

    counts = report.get("counts") or {}
    checks = report.get("checks") or []
    QualityCheckResult.objects.filter(run=run).delete()
    QualityCheckResult.objects.bulk_create(
        [
            QualityCheckResult(
                run=run,
                sequence=index,
                code=str(item.get("code", ""))[:100],
                category=str(item.get("category", ""))[:80],
                title=str(item.get("title", ""))[:180],
                status=(
                    item.get("status")
                    if item.get("status") in QualityCheckResult.Status.values
                    else QualityCheckResult.Status.ERROR
                ),
                duration_seconds=Decimal(str(item.get("duration_seconds") or 0)),
                command=list(item.get("command") or []),
                message=str(item.get("message") or "")[:4000],
                output_excerpt=str(item.get("output") or "")[-12000:],
            )
            for index, item in enumerate(checks, start=1)
        ]
    )

    run.status = QualityRun.Status.PASSED if report.get("status") == "passed" else QualityRun.Status.FAILED
    run.completed_at = timezone.now()
    run.duration_seconds = Decimal(str(report.get("duration_seconds") or 0))
    run.passed_count = int(counts.get("passed") or 0)
    run.warning_count = int(counts.get("warning") or 0)
    run.failed_count = int(counts.get("failed") or 0)
    run.skipped_count = int(counts.get("skipped") or 0)
    run.source_version = str(report.get("source_version") or settings.VINOVA_PRODUCT_VERSION)[:32]
    run.source_commit = str(report.get("source_commit") or "")[:64]
    run.environment_name = str(report.get("environment") or settings.VINOVA_QA_ENVIRONMENT)[:120]
    run.report_json_path = _safe_report_relative_path(str(report.get("report_json_path") or ""))
    run.report_html_path = _safe_report_relative_path(str(report.get("report_html_path") or ""))
    run.summary = {
        "release_ready": bool(report.get("release_ready")),
        "database": report.get("database") or {},
        "functional_e2e": report.get("functional_e2e") or {},
        "e2e_artifact_path": _safe_report_relative_path(str(report.get("e2e_artifact_path") or "")),
        "started_at": report.get("started_at"),
        "completed_at": report.get("completed_at"),
    }
    run.error_message = ""
    run.save()
    return run


@transaction.atomic
def mark_quality_run_error(run: QualityRun, message: str) -> QualityRun:
    run = QualityRun.objects.select_for_update().get(pk=run.pk)
    run.status = QualityRun.Status.ERROR
    run.completed_at = timezone.now()
    run.failed_count = max(run.failed_count, 1)
    run.error_message = message[:4000]
    run.save(update_fields=["status", "completed_at", "failed_count", "error_message", "updated_at"])
    return run


def quality_report_path(run: QualityRun, report_format: str) -> Path:
    if report_format == "json":
        relative = run.report_json_path
    elif report_format == "html":
        relative = run.report_html_path
    elif report_format == "e2e":
        relative = str((run.summary or {}).get("e2e_artifact_path") or "")
    else:
        relative = ""
    if not relative:
        raise FileNotFoundError("La ejecución no tiene ese reporte.")
    root = Path(settings.VINOVA_QA_REPORT_ROOT).resolve()
    candidate = (root / relative).resolve()
    if candidate != root and root not in candidate.parents:
        raise FileNotFoundError("Ruta de reporte inválida.")
    if not candidate.is_file():
        raise FileNotFoundError("El reporte ya no está disponible.")
    return candidate


@transaction.atomic
def cleanup_expired_quality_evidence(*, now=None) -> int:
    """ES: Ejecuta la operación «cleanup expired quality evidence» dentro del dominio de calidad. Además, conserva atomicidad y bloqueos explícitos.

    EN: Executes the «cleanup expired quality evidence» operation within the quality domain. It also preserves atomicity and explicit locking.
    """

    now = now or timezone.now()
    cutoff = now - timezone.timedelta(days=settings.VINOVA_QA_RETENTION_DAYS)
    root = Path(settings.VINOVA_QA_REPORT_ROOT).resolve()
    runs = list(
        QualityRun.objects.select_for_update()
        .filter(completed_at__lt=cutoff)
        .exclude(report_json_path="", report_html_path="")
    )
    if not runs:
        return 0

    for run in runs:
        for relative in (
            run.report_json_path,
            run.report_html_path,
            str((run.summary or {}).get("e2e_artifact_path") or ""),
        ):
            if not relative:
                continue
            candidate = (root / relative).resolve()
            if candidate != root and root in candidate.parents:
                candidate.unlink(missing_ok=True)
        run.report_json_path = ""
        run.report_html_path = ""
        summary = dict(run.summary or {})
        summary["evidence_purged_at"] = now.isoformat()
        summary["e2e_artifact_path"] = ""
        run.summary = summary
        run.save(update_fields=["report_json_path", "report_html_path", "summary", "updated_at"])

    QualityCheckResult.objects.filter(run__in=runs).update(output_excerpt="")
    return len(runs)
