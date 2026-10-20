"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de documentos.

EN: This module defines persistent models, states, and constraints for the documents domain.

Contexto existente / Existing context:
Persistent domain models and database constraints for the documents domain.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from django.db import models

from apps.common.models import SoftDeleteModel, TimeStampedModel
from apps.common.validators import validate_upload_extension, validate_upload_size
from apps.documents.storage import PrivateMediaStorage


def reusable_asset_upload_to(instance, filename):
    suffix = Path(filename).suffix.lower()
    return f"library/assets/{instance.asset_type}/{uuid4().hex}{suffix}"


def private_document_upload_to(instance, filename):
    suffix = Path(filename).suffix.lower()
    return f"documents/{instance.document_type}/{uuid4().hex}{suffix}"


class DocumentCategory(TimeStampedModel):
    class Scope(models.TextChoices):
        GENERAL = "general", "General"
        VEHICLE = "vehicle", "Vehículo"
        CUSTOMER = "customer", "Cliente"
        SALE = "sale", "Venta"
        INVOICE = "invoice", "Factura"
        COMPANY = "company", "Empresa"

    name = models.CharField(max_length=120, unique=True, db_index=True)
    scope = models.CharField(max_length=30, choices=Scope.choices, default=Scope.GENERAL, db_index=True)
    description = models.CharField(max_length=220, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["scope", "name"]
        verbose_name = "Categoría documental"
        verbose_name_plural = "Categorías documentales"

    def __str__(self):
        return self.name


class ReusableAsset(TimeStampedModel, SoftDeleteModel):
    class AssetType(models.TextChoices):
        IMAGE = "image", "Imagen"
        VEHICLE_IMAGE = "vehicle_image", "Imagen de vehículo"
        BRAND_LOGO = "brand_logo", "Logo de marca"
        MODEL_3D = "model_3d", "Modelo 3D"
        MANUAL = "manual", "Manual"
        VIDEO = "video", "Video"
        GENERAL = "general", "General"

    class Visibility(models.TextChoices):
        PUBLIC = "public", "Público"
        INTERNAL = "internal", "Interno"

    title = models.CharField(max_length=160, db_index=True)
    asset_type = models.CharField(max_length=30, choices=AssetType.choices, db_index=True)
    file = models.FileField(upload_to=reusable_asset_upload_to, validators=[validate_upload_extension, validate_upload_size])
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.INTERNAL, db_index=True)
    description = models.TextField(blank=True)
    alt_text = models.CharField(max_length=180, blank=True)
    file_hash = models.CharField(max_length=128, blank=True, db_index=True)
    original_name = models.CharField(max_length=220, blank=True)
    mime_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    extension = models.CharField(max_length=20, blank=True, db_index=True)
    branch = models.ForeignKey("branches.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="reusable_assets")
    vehicle_model = models.ForeignKey(
        "vehicles.VehicleModel",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reusable_assets",
    )
    vehicle_year = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    uploaded_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="uploaded_reusable_assets")
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["asset_type", "visibility", "is_active"]),
            models.Index(fields=["vehicle_model", "vehicle_year", "asset_type"]),
            models.Index(fields=["file_hash", "asset_type"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]
        verbose_name = "Recurso reutilizable"
        verbose_name_plural = "Recursos reutilizables"

    def __str__(self):
        return self.title

    @property
    def is_public(self):
        return self.visibility == self.Visibility.PUBLIC


class PrivateDocument(TimeStampedModel, SoftDeleteModel):
    class DocumentType(models.TextChoices):
        CONTRACT = "contract", "Contrato"
        INVOICE = "invoice", "Factura"
        RECEIPT = "receipt", "Comprobante"
        LEGAL = "legal", "Legal"
        CUSTOMER_ID = "customer_id", "Identificación de cliente"
        VEHICLE_DOC = "vehicle_doc", "Documento de vehículo"
        WARRANTY = "warranty", "Garantía"
        MANUAL = "manual", "Manual privado"
        OTHER = "other", "Otro"

    class Status(models.TextChoices):
        ACTIVE = "active", "Activo"
        PENDING_REVIEW = "pending_review", "Pendiente de revisión"
        EXPIRED = "expired", "Vencido"
        ARCHIVED = "archived", "Archivado"

    title = models.CharField(max_length=180, db_index=True)
    document_type = models.CharField(max_length=30, choices=DocumentType.choices, db_index=True)
    category = models.ForeignKey(DocumentCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name="documents")
    file = models.FileField(storage=PrivateMediaStorage(), upload_to=private_document_upload_to, validators=[validate_upload_extension, validate_upload_size])
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    branch = models.ForeignKey("branches.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="private_documents")
    customer = models.ForeignKey("customers.Customer", null=True, blank=True, on_delete=models.SET_NULL, related_name="private_documents")
    vehicle = models.ForeignKey("vehicles.Vehicle", null=True, blank=True, on_delete=models.SET_NULL, related_name="private_documents")
    sale = models.ForeignKey("sales.SaleRecord", null=True, blank=True, on_delete=models.SET_NULL, related_name="private_documents")
    notes = models.TextField(blank=True)
    expires_at = models.DateField(null=True, blank=True, db_index=True)
    is_confidential = models.BooleanField(default=True, db_index=True)
    file_hash = models.CharField(max_length=128, blank=True, db_index=True)
    original_name = models.CharField(max_length=220, blank=True)
    mime_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    extension = models.CharField(max_length=20, blank=True, db_index=True)
    uploaded_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="uploaded_private_documents")
    last_downloaded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["document_type", "status"]),
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["customer", "document_type"]),
            models.Index(fields=["vehicle", "document_type"]),
            models.Index(fields=["sale", "document_type"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]
        verbose_name = "Documento privado"
        verbose_name_plural = "Documentos privados"

    def __str__(self):
        return self.title
