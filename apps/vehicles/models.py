"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de vehículos.

EN: This module defines persistent models, states, and constraints for the vehicles domain.

Contexto existente / Existing context:
Persistent domain models and database constraints for the vehicles domain.
"""

import re
import secrets
import unicodedata

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import SoftDeleteModel, TimeStampedModel
from apps.common.validators import validate_upload_extension, validate_upload_size


class VehicleBrand(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True, db_index=True)
    logo = models.ImageField(
        upload_to="vehicles/brands/",
        blank=True,
        null=True,
        validators=[validate_upload_extension, validate_upload_size],
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Marca de vehículo"
        verbose_name_plural = "Marcas de vehículos"
        ordering = ["name"]

    def __str__(self):
        return self.name


class VehicleModel(TimeStampedModel):
    brand = models.ForeignKey(VehicleBrand, on_delete=models.PROTECT, related_name="models")
    name = models.CharField(max_length=120, db_index=True)
    segment = models.CharField(max_length=80, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["brand", "name"], name="unique_vehicle_model_per_brand")]
        verbose_name = "Modelo de vehículo"
        verbose_name_plural = "Modelos de vehículos"
        ordering = ["brand__name", "name"]

    def __str__(self):
        return f"{self.brand} {self.name}"


class VehicleResource(TimeStampedModel):
    class ResourceType(models.TextChoices):
        IMAGE = "image", "Imagen"
        MODEL_3D = "model_3d", "Modelo 3D"
        MANUAL = "manual", "Manual"
        DOCUMENT = "document", "Documento"
        VIDEO = "video", "Video"

    title = models.CharField(max_length=160)
    resource_type = models.CharField(max_length=30, choices=ResourceType.choices, db_index=True)
    file = models.FileField(
        upload_to="vehicles/resources/", validators=[validate_upload_extension, validate_upload_size]
    )
    file_hash = models.CharField(max_length=128, blank=True, db_index=True)
    mime_type = models.CharField(max_length=100, blank=True)
    is_reusable = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="uploaded_vehicle_resources"
    )

    class Meta:
        indexes = [models.Index(fields=["resource_type", "file_hash"])]
        verbose_name = "Recurso multimedia"
        verbose_name_plural = "Recursos multimedia"
        ordering = ["resource_type", "title"]

    def __str__(self):
        return self.title


class Vehicle(TimeStampedModel, SoftDeleteModel):
    """Represent an inventory vehicle and its commercial availability state."""

    class Status(models.TextChoices):
        AVAILABLE = "available", "Disponible"
        RESERVED = "reserved", "Reservado"
        SOLD = "sold", "Vendido"
        MAINTENANCE = "maintenance", "En mantenimiento"
        HIDDEN = "hidden", "Oculto"
        ARCHIVED = "archived", "Archivado"

    brand = models.ForeignKey(VehicleBrand, on_delete=models.PROTECT, related_name="vehicles")
    model = models.ForeignKey(VehicleModel, on_delete=models.PROTECT, related_name="vehicles")
    branch = models.ForeignKey(
        "branches.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="vehicles"
    )
    year = models.PositiveSmallIntegerField(db_index=True)
    version = models.CharField(max_length=120, blank=True)
    internal_code = models.CharField(max_length=80, unique=True, db_index=True, editable=False, blank=True)
    vin = models.CharField(max_length=40, unique=True, db_index=True, null=True, blank=True)
    plate = models.CharField(max_length=20, blank=True, db_index=True)
    color = models.CharField(max_length=80, blank=True)
    mileage = models.PositiveIntegerField(null=True, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.AVAILABLE, db_index=True)
    short_description = models.CharField(max_length=220, blank=True)
    description = models.TextField(blank=True)
    public_slug = models.SlugField(max_length=180, unique=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "branch"]),
            models.Index(fields=["brand", "model", "year"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-is_featured", "-created_at"]
        verbose_name = "Vehículo"
        verbose_name_plural = "Vehículos"

    def __str__(self):
        return f"{self.year} {self.brand} {self.model} {self.version}".strip()

    @staticmethod
    def _normalize_internal_code(value: str) -> str:
        value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
        return re.sub(r"[^A-Z0-9]+", "-", value.upper()).strip("-")

    def generate_internal_code(self) -> str:
        """Genera una referencia Vinova estable inspirada en Vinova Lite.

        No reemplaza el VIN real del fabricante. El código se crea una sola vez
        y se mantiene aunque después cambien datos comerciales del vehículo.
        """
        brand_name = getattr(self.brand, "name", "")
        model_name = getattr(self.model, "name", "")
        base = self._normalize_internal_code(f"VIN-{brand_name}-{model_name}-{self.year}")[:70].strip("-")
        base = base or "VIN-VEHICULO"
        candidate = base
        counter = 2
        qs = type(self).objects.all()
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        while qs.filter(internal_code__iexact=candidate).exists():
            suffix = f"-{counter:02d}"
            candidate = f"{base[: 80 - len(suffix)]}{suffix}"
            counter += 1
        return candidate

    def save(self, *args, **kwargs):
        self.vin = (self.vin or "").strip().upper() or None
        if not self.internal_code and self.brand_id and self.model_id and self.year:
            self.internal_code = self.generate_internal_code()
        return super().save(*args, **kwargs)

    def _prefetched_public_media(self) -> list["VehicleMedia"] | None:
        prefetched = getattr(self, "_prefetched_objects_cache", {}).get("media")
        if prefetched is None:
            return None
        return sorted(
            (item for item in prefetched if item.is_public),
            key=lambda item: (item.order, item.id),
        )

    @property
    def hero_media(self):
        prefetched = self._prefetched_public_media()
        media_types = {VehicleMedia.MediaType.HERO, VehicleMedia.MediaType.IMAGE}
        if prefetched is not None:
            return next((item for item in prefetched if item.media_type in media_types), None)
        return self.media.filter(is_public=True, media_type__in=media_types).order_by("order", "id").first()

    @property
    def active_model_3d(self):
        prefetched = self._prefetched_public_media()
        if prefetched is not None:
            return next((item for item in prefetched if item.media_type == VehicleMedia.MediaType.MODEL_3D), None)
        return (
            self.media.filter(is_public=True, media_type=VehicleMedia.MediaType.MODEL_3D)
            .order_by("order", "id")
            .first()
        )


class VehicleMedia(TimeStampedModel):
    class MediaType(models.TextChoices):
        HERO = "hero", "Imagen principal"
        IMAGE = "image", "Imagen"
        MODEL_3D = "model_3d", "Modelo 3D"
        FALLBACK = "fallback", "Imagen fallback 3D"
        VIDEO = "video", "Video"
        MANUAL = "manual", "Manual"

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="media")
    resource = models.ForeignKey(VehicleResource, on_delete=models.PROTECT, related_name="vehicle_media")
    media_type = models.CharField(max_length=30, choices=MediaType.choices, default=MediaType.IMAGE, db_index=True)
    title = models.CharField(max_length=140, blank=True)
    alt_text = models.CharField(max_length=180, blank=True)
    order = models.PositiveSmallIntegerField(default=0, db_index=True)
    is_public = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["order", "id"]
        indexes = [models.Index(fields=["vehicle", "media_type", "is_public", "order"])]
        verbose_name = "Multimedia de vehículo"
        verbose_name_plural = "Multimedia de vehículos"

    def __str__(self):
        return self.title or self.resource.title


class VehiclePartSpecification(TimeStampedModel):
    class PartCode(models.TextChoices):
        ENGINE = "engine", "Motor"
        TRANSMISSION = "transmission", "Transmisión"
        SUSPENSION = "suspension", "Suspensión"
        INTERIOR = "interior", "Interior"
        SAFETY = "safety", "Seguridad"
        CARGO = "cargo", "Carga"
        TECHNOLOGY = "technology", "Tecnología"
        EXTERIOR = "exterior", "Exterior"
        OTHER = "other", "Otro"

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="part_specs")
    part_code = models.CharField(max_length=40, choices=PartCode.choices, db_index=True)
    title = models.CharField(max_length=140)
    summary = models.CharField(max_length=220, blank=True)
    description = models.TextField(blank=True)
    image = models.ForeignKey(
        VehicleResource, null=True, blank=True, on_delete=models.PROTECT, related_name="vehicle_part_images"
    )
    specs = models.JSONField(default=dict, blank=True)
    hotspot_label = models.CharField(max_length=80, blank=True)
    hotspot_x = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    hotspot_y = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    hotspot_z = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        indexes = [models.Index(fields=["vehicle", "part_code", "order"])]
        verbose_name = "Especificación por parte"
        verbose_name_plural = "Especificaciones por partes"

    def __str__(self):
        return f"{self.vehicle} - {self.title}"


class VehicleLinkCode(TimeStampedModel):
    """Código privado único que permite vincular un vehículo a un cliente.

    El código es aleatorio (`secrets`), no predecible, revocable y auditado.
    La cédula o RUC por sí sola nunca demuestra propiedad: la titularidad se
    acredita canjeando un código activo o mediante transferencia autorizada.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Activo"
        USED = "used", "Usado"
        REVOKED = "revoked", "Revocado"

    _CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    _CODE_GROUPS = 4
    _CODE_GROUP_LENGTH = 4
    _COMPACT_PATTERN = re.compile(
        rf"^VNV([{_CODE_ALPHABET}]{{{_CODE_GROUPS * _CODE_GROUP_LENGTH}}})$"
    )

    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="link_codes")
    code = models.CharField(max_length=23, unique=True, editable=False, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    used_by = models.ForeignKey(
        "customers.Customer", null=True, blank=True, on_delete=models.SET_NULL, related_name="redeemed_link_codes"
    )
    used_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="revoked_vehicle_link_codes"
    )
    revocation_reason = models.CharField(max_length=220, blank=True)
    created_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="created_vehicle_link_codes"
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["vehicle"],
                condition=Q(status="active"),
                name="unique_active_link_code_per_vehicle",
            )
        ]
        indexes = [models.Index(fields=["status", "created_at"])]
        verbose_name = "Código de vinculación"
        verbose_name_plural = "Códigos de vinculación"

    def __str__(self):
        return f"{self.masked} · {self.vehicle}"

    @classmethod
    def generate_new_code(cls) -> str:
        while True:
            groups = [
                "".join(secrets.choice(cls._CODE_ALPHABET) for _ in range(cls._CODE_GROUP_LENGTH))
                for _ in range(cls._CODE_GROUPS)
            ]
            candidate = "VNV-" + "-".join(groups)
            if not cls.objects.filter(code=candidate).exists():
                return candidate

    @classmethod
    def normalize_input(cls, value: str) -> str:
        """ES: Acepta pegado flexible y devuelve el formato canónico emitido.

        EN: Accepts flexible pasted input and returns the canonical issued format.
        """

        compact = re.sub(r"[^A-Z0-9]+", "", (value or "").upper())
        match = cls._COMPACT_PATTERN.fullmatch(compact)
        if match is None:
            raise ValidationError("Usa un código válido con formato VNV-XXXX-XXXX-XXXX-XXXX.")
        payload = match.group(1)
        groups = [
            payload[index : index + cls._CODE_GROUP_LENGTH]
            for index in range(0, len(payload), cls._CODE_GROUP_LENGTH)
        ]
        return "VNV-" + "-".join(groups)

    @property
    def masked(self) -> str:
        return f"VNV-••••-••••-{self.code[-4:]}"

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and self.expires_at <= timezone.now())

    @property
    def is_usable(self) -> bool:
        return self.status == self.Status.ACTIVE and not self.is_expired


class CustomerVehicle(TimeStampedModel):
    """Vínculo persistente cliente↔vehículo (garaje digital).

    Un vehículo puede tener distintos propietarios a lo largo del tiempo; cada
    cambio se registra desactivando el vínculo anterior y creando uno nuevo sin
    borrar el historial. Los documentos privados del antiguo propietario nunca
    se trasladan al nuevo.
    """

    class RoleType(models.TextChoices):
        OWNER = "owner", "Propietario"
        PRIMARY_DRIVER = "driver", "Conductor principal"
        OTHER = "other", "Otro"

    customer = models.ForeignKey("customers.Customer", on_delete=models.CASCADE, related_name="garage_vehicles")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="customer_links")
    role_type = models.CharField(max_length=30, choices=RoleType.choices, default=RoleType.OWNER, db_index=True)
    linked_via = models.ForeignKey(
        VehicleLinkCode, null=True, blank=True, on_delete=models.SET_NULL, related_name="customer_links"
    )
    initial_mileage = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    unlinked_at = models.DateTimeField(null=True, blank=True)
    unlinked_reason = models.CharField(max_length=220, blank=True)
    snapshot_customer_name = models.CharField(max_length=220, blank=True)
    snapshot_identification = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "vehicle"],
                condition=Q(is_active=True),
                name="unique_active_customer_vehicle",
            ),
            models.UniqueConstraint(
                fields=["vehicle"],
                condition=Q(is_active=True, role_type="owner"),
                name="unique_active_vehicle_owner",
            ),
        ]
        indexes = [
            models.Index(fields=["vehicle", "is_active"]),
            models.Index(fields=["customer", "is_active"]),
        ]
        verbose_name = "Vehículo de cliente (garaje)"
        verbose_name_plural = "Vehículos del garaje"

    def __str__(self):
        return f"{self.customer.display_name} · {self.vehicle}"

    @property
    def linked_at(self):
        return self.created_at

    def refresh_snapshots(self):
        self.snapshot_customer_name = self.customer.display_name
        self.snapshot_identification = self.customer.identification_number or ""


class VehicleCommercialHighlight(TimeStampedModel):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="highlights")
    title = models.CharField(max_length=120)
    value = models.CharField(max_length=120, blank=True)
    icon = models.CharField(max_length=60, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Destacado comercial"
        verbose_name_plural = "Destacados comerciales"

    def __str__(self):
        return f"{self.vehicle} - {self.title}"
