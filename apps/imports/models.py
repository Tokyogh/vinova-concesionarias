"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de importaciones.

EN: This module defines persistent models, states, and constraints for the imports domain.

Contexto existente / Existing context:
Persistent domain models and database constraints for the imports domain.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel
from apps.common.validators import validate_upload_extension, validate_upload_size
from apps.documents.storage import PrivateMediaStorage


class ImportBatch(TimeStampedModel):
    """Lote de importación masiva con trazabilidad empresarial.

    En Vinova Pro las importaciones no deben ser scripts ocultos ni tareas que
    obliguen a tocar archivos del proyecto. Este modelo registra archivo,
    validación, previsualización, resultado y usuario responsable.
    """

    class ImportType(models.TextChoices):
        VEHICLES = "vehicles", "Vehículos"
        CUSTOMERS = "customers", "Clientes"
        INVENTORY = "inventory", "Inventario / artículos"
        STOCK = "stock", "Stock por sucursal"

    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Subido"
        VALIDATED = "validated", "Validado"
        PROCESSING = "processing", "Procesando"
        COMPLETED = "completed", "Completado"
        FAILED = "failed", "Fallido"
        CANCELLED = "cancelled", "Cancelado"

    import_type = models.CharField(max_length=30, choices=ImportType.choices, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADED, db_index=True)
    original_file = models.FileField(
        upload_to="imports/originals/%Y/%m/",
        storage=PrivateMediaStorage(),
        validators=[validate_upload_extension, validate_upload_size],
        help_text="Archivo original guardado en almacenamiento privado. No se sirve desde /media/ ni /static/.",
    )
    original_filename = models.CharField(max_length=220)
    file_hash = models.CharField(max_length=128, blank=True, db_index=True)
    file_size = models.PositiveBigIntegerField(default=0)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="import_batches")
    default_branch = models.ForeignKey("branches.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="default_import_batches", help_text="Sucursal usada cuando el archivo no trae sucursal_codigo/sucursal.")
    require_vehicle_branch = models.BooleanField(default=False, help_text="Si está activo, las importaciones de vehículos exigirán sucursal por fila o sucursal por defecto.")
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="confirmed_import_batches")
    total_rows = models.PositiveIntegerField(default=0)
    valid_rows = models.PositiveIntegerField(default=0)
    invalid_rows = models.PositiveIntegerField(default=0)
    created_count = models.PositiveIntegerField(default=0)
    updated_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    preview_rows = models.JSONField(default=list, blank=True)
    errors = models.JSONField(default=list, blank=True)
    result_summary = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    validated_at = models.DateTimeField(null=True, blank=True, db_index=True)
    confirmed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["import_type", "status"]),
            models.Index(fields=["uploaded_by", "created_at"]),
            models.Index(fields=["file_hash"]),
        ]
        verbose_name = "Lote de importación"
        verbose_name_plural = "Lotes de importación"

    def __str__(self):
        return f"{self.get_import_type_display()} · {self.original_filename}"

    @property
    def can_confirm(self):
        return self.status == self.Status.VALIDATED and self.invalid_rows == 0 and self.total_rows > 0

    def mark_completed(self):
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at", "updated_at"])


class ImportRow(TimeStampedModel):
    class RowStatus(models.TextChoices):
        VALID = "valid", "Válida"
        INVALID = "invalid", "Inválida"
        CREATED = "created", "Creada"
        UPDATED = "updated", "Actualizada"
        SKIPPED = "skipped", "Omitida"
        FAILED = "failed", "Fallida"

    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name="rows")
    row_number = models.PositiveIntegerField(db_index=True)
    status = models.CharField(max_length=20, choices=RowStatus.choices, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    normalized_payload = models.JSONField(default=dict, blank=True)
    errors = models.JSONField(default=list, blank=True)
    action = models.CharField(max_length=30, blank=True, db_index=True)
    object_label = models.CharField(max_length=120, blank=True)
    object_id = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["row_number"]
        constraints = [models.UniqueConstraint(fields=["batch", "row_number"], name="unique_import_row_per_batch")]
        indexes = [models.Index(fields=["batch", "status"]), models.Index(fields=["action"])]
        verbose_name = "Fila de importación"
        verbose_name_plural = "Filas de importación"

    def __str__(self):
        return f"Fila {self.row_number} · {self.batch}"
