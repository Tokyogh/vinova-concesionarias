"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de infraestructura compartida.

EN: This module defines persistent models, states, and constraints for the common domain.

Contexto existente / Existing context:
Persistent domain models and database constraints for the common domain.
"""

from django.db import models
from django.utils import timezone

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        abstract = True
    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
