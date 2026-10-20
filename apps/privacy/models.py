"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de privacidad.

EN: This module defines persistent models, states, and constraints for the privacy domain.

Contexto existente / Existing context:
Persistent domain models and database constraints for the privacy domain.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class ConsentRecord(TimeStampedModel):
    class Purpose(models.TextChoices):
        DATA_PROCESSING = "data_processing", "Tratamiento de datos"
        COMMERCIAL_CONTACT = "commercial_contact", "Contacto comercial"
        MARKETING = "marketing", "Marketing"
        ANALYTICS = "analytics", "Analítica"
        TEST_DRIVE = "test_drive", "Test drive"

    class Status(models.TextChoices):
        GRANTED = "granted", "Otorgado"
        REVOKED = "revoked", "Revocado"
        EXPIRED = "expired", "Expirado"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    customer = models.ForeignKey("customers.Customer", null=True, blank=True, on_delete=models.SET_NULL, related_name="consents")
    lead = models.ForeignKey("leads.Lead", null=True, blank=True, on_delete=models.SET_NULL, related_name="consent_records")
    purpose = models.CharField(max_length=32, choices=Purpose.choices, default=Purpose.DATA_PROCESSING, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.GRANTED, db_index=True)
    notice_version = models.CharField(max_length=40, default="privacy-v1")
    lawful_basis = models.CharField(max_length=120, default="consentimiento")
    source = models.CharField(max_length=80, blank=True)
    subject_name = models.CharField(max_length=180, blank=True)
    subject_email = models.EmailField(blank=True)
    accepted_at = models.DateTimeField(default=timezone.now, db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    ip_hash = models.CharField(max_length=64, blank=True)
    user_agent_hash = models.CharField(max_length=64, blank=True)
    evidence = models.JSONField(default=dict, blank=True)
    captured_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="captured_consents")

    class Meta:
        ordering = ["-accepted_at"]
        indexes = [models.Index(fields=["purpose", "status"]), models.Index(fields=["customer", "accepted_at"])]
        verbose_name = "Consentimiento"
        verbose_name_plural = "Consentimientos"

    def __str__(self):
        return f"{self.subject_name or self.subject_email or self.public_id} · {self.get_purpose_display()}"


class DataSubjectRequest(TimeStampedModel):
    class RequestType(models.TextChoices):
        ACCESS = "access", "Acceso a datos"
        EXPORT = "export", "Portabilidad / exportación"
        CORRECTION = "correction", "Corrección"
        DELETION = "deletion", "Eliminación"
        ANONYMIZATION = "anonymization", "Anonimización"
        OBJECTION = "objection", "Oposición"
        CONSENT_REVOCATION = "consent_revocation", "Revocación de consentimiento"

    class Status(models.TextChoices):
        RECEIVED = "received", "Recibida"
        IDENTITY_PENDING = "identity_pending", "Identidad pendiente"
        VERIFIED = "verified", "Identidad verificada"
        IN_PROGRESS = "in_progress", "En proceso"
        APPROVED = "approved", "Aprobada"
        COMPLETED = "completed", "Completada"
        REJECTED = "rejected", "Rechazada"
        CANCELLED = "cancelled", "Cancelada"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    request_type = models.CharField(max_length=24, choices=RequestType.choices, db_index=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.IDENTITY_PENDING, db_index=True)
    customer = models.ForeignKey("customers.Customer", null=True, blank=True, on_delete=models.SET_NULL, related_name="data_subject_requests")
    requester_name = models.CharField(max_length=180)
    requester_email = models.EmailField(blank=True, db_index=True)
    requester_phone = models.CharField(max_length=30, blank=True)
    identification_hint = models.CharField(max_length=40, blank=True, help_text="Solo una referencia parcial; no almacenes copias innecesarias.")
    description = models.TextField()
    received_at = models.DateTimeField(default=timezone.now, db_index=True)
    due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    identity_verified_at = models.DateTimeField(null=True, blank=True)
    identity_verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="verified_data_requests")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_data_requests")
    resolution = models.TextField(blank=True)
    legal_hold_reason = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=60, default="public_web")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-received_at"]
        indexes = [models.Index(fields=["status", "due_at"]), models.Index(fields=["request_type", "received_at"])]
        verbose_name = "Solicitud del titular"
        verbose_name_plural = "Solicitudes de titulares"

    def __str__(self):
        return f"{self.public_id} · {self.get_request_type_display()}"


class DataExportJob(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        PROCESSING = "processing", "Procesando"
        COMPLETED = "completed", "Completada"
        FAILED = "failed", "Fallida"
        EXPIRED = "expired", "Expirada"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    request = models.ForeignKey(DataSubjectRequest, on_delete=models.PROTECT, related_name="exports")
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="data_exports")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    file_path = models.CharField(max_length=500, blank=True)
    filename = models.CharField(max_length=240, blank=True)
    sha256 = models.CharField(max_length=64, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="generated_data_exports")
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "expires_at"])]
        verbose_name = "Exportación de datos"
        verbose_name_plural = "Exportaciones de datos"

    def __str__(self):
        return f"Exportación {self.public_id} · {self.customer}"


class RetentionPolicy(TimeStampedModel):
    class Action(models.TextChoices):
        REVIEW = "review", "Revisión manual"
        ARCHIVE = "archive", "Archivar"
        ANONYMIZE = "anonymize", "Anonimizar"
        DELETE = "delete", "Eliminar de forma controlada"

    code = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=160)
    data_category = models.CharField(max_length=120, db_index=True)
    retention_days = models.PositiveIntegerField(default=1825)
    action = models.CharField(max_length=16, choices=Action.choices, default=Action.REVIEW)
    is_active = models.BooleanField(default=True, db_index=True)
    requires_legal_review = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    last_review_at = models.DateTimeField(null=True, blank=True)
    next_review_at = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["data_category", "name"]
        verbose_name = "Política de retención"
        verbose_name_plural = "Políticas de retención"

    def __str__(self):
        return self.name


class AnonymizationRecord(TimeStampedModel):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    request = models.OneToOneField(DataSubjectRequest, on_delete=models.PROTECT, related_name="anonymization")
    customer_reference = models.CharField(max_length=80)
    before_hash = models.CharField(max_length=64)
    fields_anonymized = models.JSONField(default=list)
    warnings = models.JSONField(default=list, blank=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="performed_anonymizations")
    performed_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-performed_at"]
        verbose_name = "Registro de anonimización"
        verbose_name_plural = "Registros de anonimización"

    def __str__(self):
        return f"Anonimización {self.public_id}"
