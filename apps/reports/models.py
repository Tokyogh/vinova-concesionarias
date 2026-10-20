"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de reportes.

EN: This module defines persistent models, states, and constraints for the reports domain.

Contexto existente / Existing context:
Persistent domain models and database constraints for the reports domain.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class ReportExportJob(TimeStampedModel):
    """Registro auditable de exportaciones de reportes.

    En v0.13 las exportaciones livianas se generan de forma síncrona desde la
    web. El modelo deja preparada la trazabilidad y la futura generación pesada
    con Celery sin cambiar la interfaz de usuario.
    """

    class ReportType(models.TextChoices):
        EXECUTIVE = "executive", "Resumen ejecutivo"
        SALES = "sales", "Ventas por fecha"
        BRANCHES = "branches", "Ventas por sucursal"
        VEHICLES = "vehicles", "Vehículos por estado"
        INVENTORY = "inventory", "Inventario bajo"
        STOCK_MOVEMENTS = "stock_movements", "Movimientos de stock"
        INVOICES = "invoices", "Facturas emitidas"
        CUSTOMERS = "customers", "Clientes nuevos"
        ACTIVITY = "activity", "Actividad de usuarios"
        PRODUCTS = "products", "Productos más vendidos"

    class ExportFormat(models.TextChoices):
        CSV = "csv", "CSV"
        XLSX = "xlsx", "Excel"
        PRINT = "print", "Vista imprimible / PDF"

    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        RUNNING = "running", "En proceso"
        COMPLETED = "completed", "Completado"
        FAILED = "failed", "Fallido"

    report_type = models.CharField(max_length=40, choices=ReportType.choices, db_index=True)
    export_format = models.CharField(max_length=20, choices=ExportFormat.choices, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    filters = models.JSONField(default=dict, blank=True)
    row_count = models.PositiveIntegerField(default=0)
    file_name = models.CharField(max_length=180, blank=True)
    error_message = models.TextField(blank=True)
    requested_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="report_exports")
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["report_type", "created_at"]),
            models.Index(fields=["requested_by", "status"]),
            models.Index(fields=["export_format", "status"]),
        ]
        verbose_name = "Exportación de reporte"
        verbose_name_plural = "Exportaciones de reportes"

    def __str__(self):
        return f"{self.get_report_type_display()} · {self.get_export_format_display()} · {self.get_status_display()}"

    def mark_completed(self, *, row_count=0, file_name=""):
        self.status = self.Status.COMPLETED
        self.row_count = row_count
        self.file_name = file_name
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "row_count", "file_name", "completed_at", "updated_at"])
        return self

    def mark_failed(self, message):
        self.status = self.Status.FAILED
        self.error_message = str(message)[:2000]
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
        return self
