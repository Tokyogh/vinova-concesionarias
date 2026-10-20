"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de continuidad.

EN: This module defines persistent models, states, and constraints for the continuity domain.

Contexto existente / Existing context:
Persistent domain models and database constraints for the continuity domain.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class BackupPolicy(TimeStampedModel):
    class Frequency(models.TextChoices):
        MANUAL = "manual", "Manual"
        DAILY = "daily", "Diario"
        WEEKLY = "weekly", "Semanal"
        MONTHLY = "monthly", "Mensual"

    name = models.CharField(max_length=120, unique=True, default="Política principal")
    is_active = models.BooleanField(default=True, db_index=True)
    frequency = models.CharField(max_length=16, choices=Frequency.choices, default=Frequency.DAILY)
    retention_days = models.PositiveIntegerField(default=30)
    include_database = models.BooleanField(default=True)
    include_media = models.BooleanField(default=True)
    include_private = models.BooleanField(default=True)
    external_copy_required = models.BooleanField(default=True)
    destination_hint = models.CharField(
        max_length=240, blank=True, help_text="Ej.: R2/S3/GCS o almacenamiento externo administrado por la empresa."
    )
    last_success_at = models.DateTimeField(null=True, blank=True)
    next_review_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Política de backup"
        verbose_name_plural = "Políticas de backup"

    def __str__(self):
        return self.name


class BackupRecord(TimeStampedModel):
    """ES: Agrupa el componente «backup record» del dominio de continuidad y sus reglas relacionadas.

    EN: Groups the «backup record» component and its related rules in the continuity domain.
    """

    class BackupType(models.TextChoices):
        FULL = "full", "Completo"
        DATABASE = "database", "Base de datos"
        FILES = "files", "Archivos"

    class Status(models.TextChoices):
        PENDING = "pending", "En cola"
        RUNNING = "running", "En ejecución"
        COMPLETED = "completed", "Completado"
        FAILED = "failed", "Fallido"
        VERIFIED = "verified", "Verificado"

    class ExecutionMode(models.TextChoices):
        ASYNC = "async", "Celery asíncrono"
        SYNC_FALLBACK = "sync_fallback", "Fallback síncrono"
        COMMAND = "command", "Comando administrativo"
        SCHEDULED = "scheduled", "Programado por Celery Beat"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    policy = models.ForeignKey(BackupPolicy, null=True, blank=True, on_delete=models.SET_NULL, related_name="backups")
    backup_type = models.CharField(max_length=16, choices=BackupType.choices, default=BackupType.FULL, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    execution_mode = models.CharField(
        max_length=24, choices=ExecutionMode.choices, default=ExecutionMode.ASYNC, db_index=True
    )
    queued_at = models.DateTimeField(null=True, blank=True)
    celery_task_id = models.CharField(max_length=64, blank=True, db_index=True)
    queue_error = models.TextField(blank=True)
    archive_path = models.CharField(max_length=500, blank=True)
    filename = models.CharField(max_length=240, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    manifest = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="initiated_backups"
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="verified_backups"
    )
    error_message = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"]), models.Index(fields=["backup_type", "created_at"])]
        verbose_name = "Backup"
        verbose_name_plural = "Backups"

    def __str__(self):
        return f"{self.get_backup_type_display()} · {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def size_display(self):
        size = float(self.size_bytes or 0)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024 or unit == "TB":
                return f"{size:.1f} {unit}"
            size /= 1024


class RestoreDrill(TimeStampedModel):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planificado"
        RUNNING = "running", "En ejecución"
        PASSED = "passed", "Aprobado"
        FAILED = "failed", "Fallido"
        CANCELLED = "cancelled", "Cancelado"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    backup = models.ForeignKey(BackupRecord, on_delete=models.PROTECT, related_name="restore_drills")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PLANNED, db_index=True)
    environment = models.CharField(max_length=120, default="Entorno aislado de pruebas")
    planned_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="restore_drills"
    )
    checklist = models.JSONField(default=list, blank=True)
    result_summary = models.TextField(blank=True)
    evidence_hash = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]
        verbose_name = "Simulacro de restauración"
        verbose_name_plural = "Simulacros de restauración"

    def __str__(self):
        return f"Restore drill {self.public_id} · {self.get_status_display()}"
