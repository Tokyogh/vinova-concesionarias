"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de clientes.

EN: This module defines persistent models, states, and constraints for the customers domain.

Contexto existente / Existing context:
Persistent domain models and database constraints for the customers domain.
"""

from django.db import models
from django.db.models import Q

from apps.common.models import SoftDeleteModel, TimeStampedModel
from apps.common.normalization import normalize_email, normalize_phone


class Customer(TimeStampedModel, SoftDeleteModel):
    """Store the customer dossier optionally linked to one portal account."""

    class CustomerType(models.TextChoices):
        NATURAL = "natural", "Persona natural"
        COMPANY = "company", "Empresa"

    class IdentificationType(models.TextChoices):
        CEDULA = "cedula", "Cédula"
        RUC = "ruc", "RUC"
        PASSPORT = "passport", "Pasaporte"
        OTHER = "other", "Otro"

    class Status(models.TextChoices):
        PROSPECT = "prospect", "Prospecto"
        ACTIVE = "active", "Activo"
        VIP = "vip", "VIP"
        INACTIVE = "inactive", "Inactivo"
        ARCHIVED = "archived", "Archivado"

    class ContactMethod(models.TextChoices):
        PHONE = "phone", "Teléfono"
        WHATSAPP = "whatsapp", "WhatsApp"
        EMAIL = "email", "Correo"
        IN_PERSON = "in_person", "Presencial"

    customer_type = models.CharField(max_length=20, choices=CustomerType.choices, default=CustomerType.NATURAL, db_index=True)
    identification_type = models.CharField(max_length=20, choices=IdentificationType.choices, blank=True)
    identification_number = models.CharField(max_length=30, null=True, blank=True, db_index=True)
    first_name = models.CharField(max_length=100, blank=True, db_index=True)
    last_name = models.CharField(max_length=120, blank=True, db_index=True)
    business_name = models.CharField(max_length=180, blank=True, db_index=True)
    email = models.EmailField(blank=True, db_index=True)
    phone = models.CharField(max_length=30, blank=True, db_index=True)
    whatsapp = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=220, blank=True)
    city = models.CharField(max_length=90, blank=True, db_index=True)
    province = models.CharField(max_length=90, blank=True, db_index=True)
    preferred_contact_method = models.CharField(max_length=20, choices=ContactMethod.choices, default=ContactMethod.WHATSAPP)
    source = models.CharField(max_length=120, blank=True, help_text="Ej.: web, llamada, sala de ventas, referido, feria automotriz.")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROSPECT, db_index=True)
    assigned_branch = models.ForeignKey("branches.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="customers")
    assigned_advisor = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_customers")
    account = models.OneToOneField(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="customer_profile",
        help_text="Cuenta de acceso que representa a este cliente en el portal.",
    )
    internal_notes = models.TextField(blank=True)
    created_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="created_customers")

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["identification_number"],
                condition=Q(identification_number__isnull=False) & ~Q(identification_number=""),
                name="unique_customer_identification_when_present",
            )
        ]
        indexes = [
            models.Index(fields=["customer_type", "status"]),
            models.Index(fields=["assigned_branch", "status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["email"]),
            models.Index(fields=["phone"]),
        ]
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    def __str__(self):
        return self.display_name

    def clean(self):
        self.email = normalize_email(self.email)
        self.phone = normalize_phone(self.phone)
        self.whatsapp = normalize_phone(self.whatsapp)
        from apps.customers.identification import validate_customer_identification

        validate_customer_identification(self)

    def save(self, *args, **kwargs):
        self.email = normalize_email(self.email)
        self.phone = normalize_phone(self.phone)
        self.whatsapp = normalize_phone(self.whatsapp)
        if self.identification_number:
            from apps.customers.identification import normalize_for_storage

            self.identification_number = normalize_for_storage(
                self.identification_type or "", self.identification_number
            ) or None
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        if self.customer_type == self.CustomerType.COMPANY:
            return self.business_name or self.identification_number or "Empresa sin nombre"
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.identification_number or "Cliente sin nombre"

    @property
    def primary_contact(self):
        return self.whatsapp or self.phone or self.email or "Sin contacto"


class CustomerVehicleInterest(TimeStampedModel):
    class InterestStatus(models.TextChoices):
        OPEN = "open", "Abierto"
        QUOTED = "quoted", "Cotizado"
        RESERVED = "reserved", "Reservado"
        CLOSED = "closed", "Cerrado"
        CANCELLED = "cancelled", "Cancelado"

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="vehicle_interests")
    vehicle = models.ForeignKey("vehicles.Vehicle", null=True, blank=True, on_delete=models.SET_NULL, related_name="customer_interests")
    brand = models.CharField(max_length=120, blank=True)
    model_name = models.CharField(max_length=120, blank=True)
    year_from = models.PositiveSmallIntegerField(null=True, blank=True)
    year_to = models.PositiveSmallIntegerField(null=True, blank=True)
    budget_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    budget_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=InterestStatus.choices, default=InterestStatus.OPEN, db_index=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="created_customer_interests")

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["customer", "status"]), models.Index(fields=["created_at"])]
        verbose_name = "Interés vehicular"
        verbose_name_plural = "Intereses vehiculares"

    def __str__(self):
        target = self.vehicle or " ".join([self.brand, self.model_name]).strip() or "Interés sin vehículo definido"
        return f"{self.customer.display_name} · {target}"


class CustomerNote(TimeStampedModel):
    class NoteType(models.TextChoices):
        GENERAL = "general", "General"
        CALL = "call", "Llamada"
        VISIT = "visit", "Visita"
        EMAIL = "email", "Correo"
        WHATSAPP = "whatsapp", "WhatsApp"
        WARNING = "warning", "Importante"

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="notes")
    note_type = models.CharField(max_length=20, choices=NoteType.choices, default=NoteType.GENERAL, db_index=True)
    title = models.CharField(max_length=140, blank=True)
    body = models.TextField()
    is_important = models.BooleanField(default=False, db_index=True)
    created_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="customer_notes")

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["customer", "created_at"]), models.Index(fields=["note_type", "is_important"])]
        verbose_name = "Nota de cliente"
        verbose_name_plural = "Notas de clientes"

    def __str__(self):
        return self.title or f"Nota de {self.customer.display_name}"
