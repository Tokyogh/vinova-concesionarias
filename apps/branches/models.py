"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de sucursales.

EN: This module defines persistent models, states, and constraints for the branches domain.

Contexto existente / Existing context:
Modelos persistentes y restricciones del dominio de sedes.

Persistent models and database constraints for the branches domain.
"""

import re

from django.core.validators import MaxValueValidator, MinValueValidator, URLValidator
from django.db import models

from apps.common.models import TimeStampedModel
from apps.common.validators import validate_upload_extension, validate_upload_size


class Branch(TimeStampedModel):
    """ES: Agrupa el componente «branch» del dominio de sucursales y sus reglas relacionadas.

    EN: Groups the «branch» component and its related rules in the branches domain.
    """

    class BranchType(models.TextChoices):
        AFFILIATED_INSTITUTION = "institution", "Institución afiliada"
        DEALERSHIP = "dealership", "Concesionaria"
        SERVICE_CENTER = "service_center", "Centro de atención"
        WAREHOUSE = "warehouse", "Bodega"
        OFFICE = "office", "Oficina"

    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=140, db_index=True)
    code = models.SlugField(max_length=60, db_index=True)
    branch_type = models.CharField(max_length=40, choices=BranchType.choices, default=BranchType.DEALERSHIP, db_index=True)
    city = models.CharField(max_length=80, db_index=True)
    province = models.CharField(max_length=80, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    description = models.TextField(blank=True)
    opening_hours = models.CharField(max_length=180, blank=True)
    services = models.JSONField(default=list, blank=True)
    photo = models.ImageField(
        upload_to="branches/photos/",
        blank=True,
        null=True,
        validators=[validate_upload_extension, validate_upload_size],
    )
    website_url = models.URLField(
        max_length=500,
        blank=True,
        validators=[URLValidator(schemes=["http", "https"])],
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    is_public = models.BooleanField(default=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["company", "code"], name="unique_branch_code_per_company")]
        indexes = [models.Index(fields=["city", "branch_type", "is_active"])]
        verbose_name = "Sucursal"
        verbose_name_plural = "Sucursales"

    def __str__(self):
        return f"{self.name} - {self.city}"

    @property
    def public_category(self):
        return {
            self.BranchType.AFFILIATED_INSTITUTION: "institution",
            self.BranchType.OFFICE: "institution",
            self.BranchType.DEALERSHIP: "dealership",
            self.BranchType.SERVICE_CENTER: "service_center",
        }.get(self.branch_type, "")

    @property
    def public_category_label(self):
        return {
            "institution": "Institución afiliada",
            "dealership": "Concesionario",
            "service_center": "Centro de atención",
        }.get(self.public_category, "Establecimiento")

    @property
    def public_services(self):
        values = self.services if isinstance(self.services, list) else []
        return [str(value).strip()[:80] for value in values if str(value).strip()][:6]

    @property
    def phone_uri(self):
        return re.sub(r"[^+\d]", "", self.phone or "")

    @property
    def has_map_coordinates(self):
        return self.latitude is not None and self.longitude is not None
