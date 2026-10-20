"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de CRM y leads.

EN: This module defines persistent models, states, and constraints for the leads domain.

Contexto existente / Existing context:
Persistent domain models and database constraints for the leads domain.
"""

from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.common.models import SoftDeleteModel, TimeStampedModel
from apps.common.normalization import normalize_email, normalize_phone


class Lead(TimeStampedModel, SoftDeleteModel):
    """Track a commercial opportunity through its validated lifecycle."""

    class RequestType(models.TextChoices):
        INFORMATION = "information", "Solicitar información"
        QUOTE = "quote", "Solicitar cotización"
        TEST_DRIVE = "test_drive", "Agendar test drive"
        FINANCING = "financing", "Consultar financiamiento"
        OTHER = "other", "Otra solicitud"

    class Status(models.TextChoices):
        NEW = "new", "Nuevo"
        CONTACTED = "contacted", "Contactado"
        INTERESTED = "interested", "Interesado"
        QUOTED = "quoted", "Cotización enviada"
        TEST_DRIVE = "test_drive", "Test drive agendado"
        NEGOTIATION = "negotiation", "Negociación"
        WON = "won", "Ganado"
        LOST = "lost", "Perdido"

    class Priority(models.TextChoices):
        LOW = "low", "Baja"
        MEDIUM = "medium", "Media"
        HIGH = "high", "Alta"
        URGENT = "urgent", "Urgente"

    class Source(models.TextChoices):
        WEB_CATALOG = "web_catalog", "Catálogo web"
        WEBSITE = "website", "Sitio web"
        SHOWROOM = "showroom", "Sala de ventas"
        PHONE = "phone", "Teléfono"
        WHATSAPP = "whatsapp", "WhatsApp"
        REFERRAL = "referral", "Referido"
        FAIR = "fair", "Feria / evento"
        IMPORT = "import", "Importación"
        OTHER = "other", "Otro"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    code = models.CharField(max_length=40, unique=True, editable=False, db_index=True, blank=True)
    request_type = models.CharField(max_length=24, choices=RequestType.choices, default=RequestType.INFORMATION, db_index=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.NEW, db_index=True)
    priority = models.CharField(max_length=16, choices=Priority.choices, default=Priority.MEDIUM, db_index=True)
    source = models.CharField(max_length=24, choices=Source.choices, default=Source.WEBSITE, db_index=True)

    full_name = models.CharField(max_length=180, db_index=True)
    email = models.EmailField(blank=True, db_index=True)
    phone = models.CharField(max_length=30, blank=True, db_index=True)
    whatsapp = models.CharField(max_length=30, blank=True)
    city = models.CharField(max_length=90, blank=True, db_index=True)
    province = models.CharField(max_length=90, blank=True, db_index=True)
    preferred_contact_method = models.CharField(max_length=20, blank=True, default="whatsapp")

    customer = models.ForeignKey("customers.Customer", null=True, blank=True, on_delete=models.SET_NULL, related_name="crm_leads")
    vehicle = models.ForeignKey("vehicles.Vehicle", null=True, blank=True, on_delete=models.SET_NULL, related_name="crm_leads")
    branch = models.ForeignKey("branches.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="crm_leads")
    assigned_advisor = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_leads")
    linked_sale = models.ForeignKey("sales.SaleRecord", null=True, blank=True, on_delete=models.SET_NULL, related_name="origin_leads")

    interested_brand = models.CharField(max_length=120, blank=True)
    interested_model = models.CharField(max_length=120, blank=True)
    budget_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    budget_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    expected_purchase_date = models.DateField(null=True, blank=True)
    message = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    lost_reason = models.CharField(max_length=240, blank=True)
    score = models.PositiveSmallIntegerField(default=0, db_index=True)

    consent_data_processing = models.BooleanField(default=False)
    consent_at = models.DateTimeField(null=True, blank=True)
    source_url = models.CharField(max_length=500, blank=True)
    referrer = models.CharField(max_length=500, blank=True)
    utm_source = models.CharField(max_length=120, blank=True)
    utm_medium = models.CharField(max_length=120, blank=True)
    utm_campaign = models.CharField(max_length=160, blank=True)
    session_hash = models.CharField(max_length=64, blank=True, db_index=True)
    ip_hash = models.CharField(max_length=64, blank=True, db_index=True)

    last_contact_at = models.DateTimeField(null=True, blank=True, db_index=True)
    next_follow_up_at = models.DateTimeField(null=True, blank=True, db_index=True)
    closed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="created_leads")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "priority"]),
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["assigned_advisor", "status"]),
            models.Index(fields=["vehicle", "status"]),
            models.Index(fields=["source", "created_at"]),
            models.Index(fields=["next_follow_up_at", "status"]),
            models.Index(fields=["city", "status"]),
        ]
        verbose_name = "Lead"
        verbose_name_plural = "Leads"

    def __str__(self):
        return f"{self.code or 'Lead'} · {self.full_name}"

    @property
    def is_closed(self):
        return self.status in {self.Status.WON, self.Status.LOST}

    @property
    def contact_value(self):
        return self.whatsapp or self.phone or self.email or "Sin contacto"

    @property
    def vehicle_interest_label(self):
        if self.vehicle_id:
            return str(self.vehicle)
        return " ".join(filter(None, [self.interested_brand, self.interested_model])).strip() or "Interés general"

    def clean(self):
        self.email = normalize_email(self.email)
        self.phone = normalize_phone(self.phone)
        self.whatsapp = normalize_phone(self.whatsapp)
        if not (self.email or self.phone or self.whatsapp):
            raise ValidationError("El lead necesita al menos correo, teléfono o WhatsApp.")
        if self.budget_min is not None and self.budget_max is not None and self.budget_min > self.budget_max:
            raise ValidationError({"budget_max": "El presupuesto máximo debe ser mayor o igual al mínimo."})
        if self.status == self.Status.LOST and not self.lost_reason:
            raise ValidationError({"lost_reason": "Registra el motivo de pérdida."})

    def save(self, *args, **kwargs):
        self.full_name = " ".join((self.full_name or "").split())
        self.email = normalize_email(self.email)
        self.phone = normalize_phone(self.phone)
        self.whatsapp = normalize_phone(self.whatsapp)
        if not self.code:
            date_part = timezone.localdate().strftime("%Y%m%d")
            self.code = f"LEAD-{date_part}-{self.public_id.hex[:8].upper()}"
        if self.consent_data_processing and not self.consent_at:
            self.consent_at = timezone.now()
        super().save(*args, **kwargs)


class LeadActivity(TimeStampedModel):
    class ActivityType(models.TextChoices):
        NOTE = "note", "Nota"
        CALL = "call", "Llamada"
        EMAIL = "email", "Correo"
        WHATSAPP = "whatsapp", "WhatsApp"
        VISIT = "visit", "Visita"
        STATUS = "status", "Cambio de estado"
        ASSIGNMENT = "assignment", "Asignación"
        FOLLOW_UP = "follow_up", "Seguimiento"
        QUOTE = "quote", "Cotización"
        TEST_DRIVE = "test_drive", "Test drive"
        CONVERSION = "conversion", "Conversión"
        SYSTEM = "system", "Sistema"

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="activities")
    activity_type = models.CharField(max_length=24, choices=ActivityType.choices, default=ActivityType.NOTE, db_index=True)
    title = models.CharField(max_length=180)
    detail = models.TextField(blank=True)
    outcome = models.CharField(max_length=180, blank=True)
    previous_status = models.CharField(max_length=24, choices=Lead.Status.choices, blank=True)
    new_status = models.CharField(max_length=24, choices=Lead.Status.choices, blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="lead_activities")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["lead", "created_at"]), models.Index(fields=["activity_type", "scheduled_for"])]
        verbose_name = "Actividad de lead"
        verbose_name_plural = "Actividades de leads"

    def __str__(self):
        return f"{self.lead.code} · {self.title}"


class TestDrive(TimeStampedModel):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Agendado"
        CONFIRMED = "confirmed", "Confirmado"
        COMPLETED = "completed", "Completado"
        CANCELLED = "cancelled", "Cancelado"
        NO_SHOW = "no_show", "No asistió"

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="test_drives")
    vehicle = models.ForeignKey("vehicles.Vehicle", on_delete=models.PROTECT, related_name="test_drives")
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="test_drives")
    advisor = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="test_drives")
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED, db_index=True)
    notes = models.TextField(blank=True)
    result_notes = models.TextField(blank=True)
    created_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="created_test_drives")

    class Meta:
        ordering = ["starts_at"]
        indexes = [models.Index(fields=["branch", "starts_at", "status"]), models.Index(fields=["advisor", "starts_at"])]
        verbose_name = "Test drive"
        verbose_name_plural = "Test drives"

    def clean(self):
        if self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "La hora final debe ser posterior a la inicial."})
        if self.vehicle_id and self.branch_id and self.vehicle.branch_id and self.vehicle.branch_id != self.branch_id:
            raise ValidationError({"vehicle": "El vehículo pertenece a otra sucursal."})

    def __str__(self):
        return f"{self.lead.code} · {self.vehicle} · {self.starts_at:%d/%m/%Y %H:%M}"
