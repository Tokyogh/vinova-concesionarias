"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de calidad.

EN: This module defines persistent models, states, and constraints for the quality domain.

Contexto existente / Existing context:
Persistent domain models and database constraints for the quality domain.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class QualityRun(TimeStampedModel):
    """ES: Agrupa el componente «quality run» del dominio de calidad y sus reglas relacionadas.

    EN: Groups the «quality run» component and its related rules in the quality domain.
    """

    class Profile(models.TextChoices):
        QUICK = "quick", "Rápida"
        FULL = "full", "Completa"
        RELEASE = "release", "Release"

    class Status(models.TextChoices):
        QUEUED = "queued", "En cola"
        RUNNING = "running", "En ejecución"
        PASSED = "passed", "Aprobada"
        FAILED = "failed", "Fallida"
        ERROR = "error", "Error operativo"
        CANCELLED = "cancelled", "Cancelada"

    class Trigger(models.TextChoices):
        PANEL = "panel", "Panel interno"
        API = "api", "API interna"
        CLI = "cli", "Línea de comandos"
        SCHEDULED = "scheduled", "Programada"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    profile = models.CharField(max_length=16, choices=Profile.choices, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED, db_index=True)
    trigger = models.CharField(max_length=16, choices=Trigger.choices, default=Trigger.PANEL, db_index=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="quality_runs",
    )
    celery_task_id = models.CharField(max_length=255, blank=True)
    source_version = models.CharField(max_length=32, blank=True)
    source_commit = models.CharField(max_length=64, blank=True)
    environment_name = models.CharField(max_length=120, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    passed_count = models.PositiveIntegerField(default=0)
    warning_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    report_json_path = models.CharField(max_length=500, blank=True)
    report_html_path = models.CharField(max_length=500, blank=True)
    summary = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["profile", "created_at"]),
        ]
        verbose_name = "Ejecución QA"
        verbose_name_plural = "Ejecuciones QA"

    def __str__(self):
        return f"QA {self.get_profile_display()} · {self.public_id}"

    @property
    def release_ready(self) -> bool:
        return (
            self.profile == self.Profile.RELEASE
            and self.status == self.Status.PASSED
            and self.failed_count == 0
            and self.warning_count == 0
            and bool(self.summary.get("release_ready"))
        )


class QualityCheckResult(TimeStampedModel):
    class Status(models.TextChoices):
        PASSED = "passed", "Aprobada"
        WARNING = "warning", "Advertencia"
        FAILED = "failed", "Fallida"
        SKIPPED = "skipped", "Omitida"
        ERROR = "error", "Error"

    run = models.ForeignKey(QualityRun, on_delete=models.CASCADE, related_name="checks")
    sequence = models.PositiveIntegerField(default=0)
    code = models.SlugField(max_length=100)
    category = models.CharField(max_length=80)
    title = models.CharField(max_length=180)
    status = models.CharField(max_length=16, choices=Status.choices, db_index=True)
    duration_seconds = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    command = models.JSONField(default=list, blank=True)
    message = models.TextField(blank=True)
    output_excerpt = models.TextField(blank=True)

    class Meta:
        ordering = ["sequence", "id"]
        constraints = [models.UniqueConstraint(fields=["run", "code"], name="quality_unique_check_per_run")]
        indexes = [models.Index(fields=["run", "status"])]
        verbose_name = "Resultado de control QA"
        verbose_name_plural = "Resultados de controles QA"

    def __str__(self):
        return f"{self.run.public_id} · {self.code} · {self.status}"
