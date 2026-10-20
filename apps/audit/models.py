"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de auditoría.

EN: This module defines persistent models, states, and constraints for the audit domain.

Contexto existente / Existing context:
Persistent domain models and database constraints for the audit domain.
"""

from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class AuditLog(TimeStampedModel):
    """ES: Agrupa el componente «audit log» del dominio de auditoría y sus reglas relacionadas. Además, registra efectos auditables.

    EN: Groups the «audit log» component and its related rules in the audit domain. It also records auditable effects.
    """

    class Category(models.TextChoices):
        AUTHENTICATION = "authentication", "Autenticación"
        AUTHORIZATION = "authorization", "Permisos y acceso"
        DATA_CHANGE = "data_change", "Cambio de datos"
        DOCUMENT = "document", "Documento privado"
        INVENTORY = "inventory", "Inventario"
        SALES = "sales", "Ventas y facturación"
        IMPORT = "import", "Importaciones"
        CONFIGURATION = "configuration", "Configuración"
        SECURITY = "security", "Seguridad"
        REPORT = "report", "Reportes y exportaciones"
        SYSTEM = "system", "Sistema"

    class Severity(models.TextChoices):
        INFO = "info", "Informativo"
        LOW = "low", "Bajo"
        MEDIUM = "medium", "Medio"
        HIGH = "high", "Alto"
        CRITICAL = "critical", "Crítico"

    class Result(models.TextChoices):
        SUCCESS = "success", "Correcto"
        DENIED = "denied", "Denegado"
        FAILED = "failed", "Fallido"
        WARNING = "warning", "Advertencia"

    event_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    user = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs")
    username_snapshot = models.CharField(max_length=150, blank=True, db_index=True)
    user_display_snapshot = models.CharField(max_length=220, blank=True)
    role_snapshot = models.JSONField(default=list, blank=True)
    branch = models.ForeignKey("branches.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs")
    customer = models.ForeignKey("customers.Customer", null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs")

    action = models.CharField(max_length=160, db_index=True)
    category = models.CharField(max_length=40, choices=Category.choices, default=Category.DATA_CHANGE, db_index=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.INFO, db_index=True)
    result = models.CharField(max_length=20, choices=Result.choices, default=Result.SUCCESS, db_index=True)

    object_repr = models.CharField(max_length=250, blank=True)
    content_type_label = models.CharField(max_length=120, blank=True, db_index=True)
    object_id = models.CharField(max_length=80, blank=True, db_index=True)

    request_id = models.UUIDField(null=True, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    user_agent = models.TextField(blank=True)
    http_method = models.CharField(max_length=12, blank=True)
    request_path = models.CharField(max_length=500, blank=True, db_index=True)

    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_sensitive = models.BooleanField(default=False, db_index=True)

    integrity_version = models.PositiveSmallIntegerField(default=1)
    previous_hash = models.CharField(max_length=64, blank=True)
    entry_hash = models.CharField(max_length=64, blank=True, unique=True, null=True)

    class Meta:
        ordering = ["-occurred_at", "-id"]
        indexes = [
            models.Index(fields=["action", "occurred_at"]),
            models.Index(fields=["content_type_label", "object_id"]),
            models.Index(fields=["category", "severity", "occurred_at"]),
            models.Index(fields=["user", "occurred_at"]),
            models.Index(fields=["branch", "occurred_at"]),
            models.Index(fields=["result", "occurred_at"]),
        ]
        verbose_name = "Registro de auditoría"
        verbose_name_plural = "Auditoría"

    def __str__(self):
        return f"{self.action} - {self.object_repr or self.username_snapshot or 'Sistema'}"


class SecurityAlert(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Abierta"
        IN_REVIEW = "in_review", "En revisión"
        RESOLVED = "resolved", "Resuelta"
        FALSE_POSITIVE = "false_positive", "Falso positivo"

    alert_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    audit_log = models.OneToOneField(AuditLog, null=True, blank=True, on_delete=models.SET_NULL, related_name="security_alert")
    code = models.CharField(max_length=100, db_index=True)
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    severity = models.CharField(max_length=20, choices=AuditLog.Severity.choices, default=AuditLog.Severity.HIGH, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)
    branch = models.ForeignKey("branches.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="security_alerts")
    user = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="security_alerts")
    assigned_to = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_security_alerts")
    resolved_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="resolved_security_alerts")
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    occurrence_count = models.PositiveIntegerField(default=1)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "severity", "created_at"]),
            models.Index(fields=["code", "created_at"]),
            models.Index(fields=["branch", "status"]),
        ]
        verbose_name = "Alerta de seguridad"
        verbose_name_plural = "Alertas de seguridad"

    def __str__(self):
        return f"{self.get_severity_display()}: {self.title}"

    def resolve(self, *, actor, status: str, notes: str = "") -> None:
        self.status = status
        self.resolution_notes = notes
        if status in {self.Status.RESOLVED, self.Status.FALSE_POSITIVE}:
            self.resolved_at = timezone.now()
            self.resolved_by = actor if getattr(actor, "is_authenticated", False) else None
        else:
            self.resolved_at = None
            self.resolved_by = None
        self.save(update_fields=["status", "resolution_notes", "resolved_at", "resolved_by", "updated_at"])
