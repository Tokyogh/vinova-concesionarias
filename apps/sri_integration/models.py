"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de configuración SRI heredada.

EN: This module defines persistent models, states, and constraints for the sri integration domain.

Contexto existente / Existing context:
Persistent domain models and database constraints for the sri integration domain.
"""

from __future__ import annotations

from django.db import models

from apps.common.models import TimeStampedModel
from apps.common.validators import validate_upload_extension, validate_upload_size
from apps.documents.storage import PrivateMediaStorage


def sri_certificate_upload_to(instance, filename):
    return f"sri/certificates/company_{instance.company_id}/{filename}"


class SriConfiguration(TimeStampedModel):
    """Base de compatibilidad SRI para Ecuador.

    Esta app no afirma emisión oficial terminada. Deja lista la estructura para
    que la empresa complete datos reales, certificado, pruebas y validaciones
    tributarias con su equipo autorizado.
    """

    class Environment(models.TextChoices):
        TEST = "test", "Pruebas"
        PRODUCTION = "production", "Producción"

    class Status(models.TextChoices):
        NOT_CONFIGURED = "not_configured", "No configurado"
        DRAFT = "draft", "Borrador"
        READY_FOR_TESTS = "ready_for_tests", "Listo para pruebas"
        READY_FOR_PRODUCTION = "ready_for_production", "Listo para producción"
        ERROR = "error", "Con errores"

    company = models.OneToOneField("companies.Company", on_delete=models.CASCADE, related_name="sri_configuration")
    ruc = models.CharField(max_length=13, db_index=True)
    legal_name = models.CharField(max_length=180)
    commercial_name = models.CharField(max_length=140, blank=True)
    matrix_address = models.TextField(blank=True)
    environment = models.CharField(max_length=20, choices=Environment.choices, default=Environment.TEST, db_index=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.NOT_CONFIGURED, db_index=True)
    emission_type = models.CharField(max_length=10, default="1", help_text="Tipo de emisión SRI. Normalmente 1 = normal.")
    accounting_required = models.BooleanField(default=False)
    special_taxpayer_resolution = models.CharField(max_length=60, blank=True)
    withholding_agent_resolution = models.CharField(max_length=60, blank=True)
    taxpayer_regime = models.CharField(max_length=120, blank=True)
    electronic_signature_provider = models.CharField(max_length=120, blank=True)
    certificate_file = models.FileField(
        storage=PrivateMediaStorage(),
        upload_to=sri_certificate_upload_to,
        validators=[validate_upload_extension, validate_upload_size],
        blank=True,
        null=True,
    )
    certificate_password_reference = models.CharField(
        max_length=180,
        blank=True,
        help_text="Referencia segura a la clave del certificado. No guardar claves reales en texto plano.",
    )
    certificate_expires_at = models.DateField(null=True, blank=True)
    technical_contact_name = models.CharField(max_length=120, blank=True)
    technical_contact_email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)
    last_validation_message = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=["ruc", "environment", "status"]), models.Index(fields=["status"])]
        verbose_name = "Configuración SRI"
        verbose_name_plural = "Configuraciones SRI"

    def __str__(self):
        return f"SRI {self.company.commercial_name} ({self.get_environment_display()})"


class SriEstablishment(TimeStampedModel):
    configuration = models.ForeignKey(SriConfiguration, on_delete=models.CASCADE, related_name="establishments")
    establishment_code = models.CharField(max_length=3, db_index=True)
    emission_point_code = models.CharField(max_length=3, db_index=True)
    name = models.CharField(max_length=140)
    address = models.TextField(blank=True)
    branch = models.ForeignKey("branches.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="sri_establishments")
    is_default = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["configuration", "establishment_code", "emission_point_code"],
                name="unique_sri_establishment_emission_point",
            )
        ]
        indexes = [models.Index(fields=["configuration", "is_active"]), models.Index(fields=["establishment_code", "emission_point_code"])]
        ordering = ["establishment_code", "emission_point_code"]
        verbose_name = "Establecimiento SRI"
        verbose_name_plural = "Establecimientos SRI"

    def __str__(self):
        return f"{self.establishment_code}-{self.emission_point_code} · {self.name}"


class SriSequence(TimeStampedModel):
    class DocumentType(models.TextChoices):
        INVOICE = "invoice", "Factura"
        CREDIT_NOTE = "credit_note", "Nota de crédito"
        DEBIT_NOTE = "debit_note", "Nota de débito"
        RETENTION = "retention", "Retención"
        WAYBILL = "waybill", "Guía de remisión"
        INTERNAL_RECEIPT = "internal_receipt", "Comprobante interno"

    establishment = models.ForeignKey(SriEstablishment, on_delete=models.CASCADE, related_name="sequences")
    document_type = models.CharField(max_length=30, choices=DocumentType.choices, db_index=True)
    current_number = models.PositiveIntegerField(default=0)
    start_number = models.PositiveIntegerField(default=1)
    max_number = models.PositiveIntegerField(default=999999999)
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["establishment", "document_type"], name="unique_sri_sequence_document_type")]
        indexes = [models.Index(fields=["document_type", "is_active"])]
        ordering = ["establishment", "document_type"]
        verbose_name = "Secuencia SRI"
        verbose_name_plural = "Secuencias SRI"

    def __str__(self):
        return f"{self.establishment} · {self.get_document_type_display()}"

    @property
    def next_number_preview(self):
        next_number = max(self.current_number + 1, self.start_number)
        return f"{self.establishment.establishment_code}-{self.establishment.emission_point_code}-{next_number:09d}"
