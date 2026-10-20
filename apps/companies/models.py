"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de empresa.

EN: This module defines persistent models, states, and constraints for the companies domain.

Contexto existente / Existing context:
Persistent domain models and database constraints for the companies domain.
"""

from django.db import models

from apps.common.models import TimeStampedModel
from apps.common.validators import validate_hex_color, validate_upload_extension, validate_upload_size


class Company(TimeStampedModel):
    legal_name = models.CharField(max_length=180)
    commercial_name = models.CharField(max_length=140, db_index=True)
    ruc = models.CharField(max_length=20, unique=True, db_index=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    address = models.TextField(blank=True)
    logo = models.ImageField(
        upload_to="company/logos/",
        blank=True,
        null=True,
        validators=[validate_upload_extension, validate_upload_size],
    )
    primary_color = models.CharField(max_length=20, default="#0f3b66", validators=[validate_hex_color])
    secondary_color = models.CharField(max_length=20, default="#f2f5f8", validators=[validate_hex_color])
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self):
        return self.commercial_name
