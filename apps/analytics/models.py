"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de analítica.

EN: This module defines persistent models, states, and constraints for the analytics domain.

Contexto existente / Existing context:
Persistent domain models and database constraints for the analytics domain.
"""

from __future__ import annotations

import uuid

from django.db import models

from apps.common.models import TimeStampedModel


class VehicleInteraction(TimeStampedModel):
    class EventType(models.TextChoices):
        DETAIL_VIEW = "detail_view", "Vista de ficha"
        INFO_CLICK = "info_click", "Clic en solicitar información"
        LEAD_SUBMITTED = "lead_submitted", "Solicitud enviada"
        QUOTE_REQUEST = "quote_request", "Cotización solicitada"
        TEST_DRIVE_REQUEST = "test_drive_request", "Test drive solicitado"

    event_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    event_type = models.CharField(max_length=32, choices=EventType.choices, db_index=True)
    vehicle = models.ForeignKey("vehicles.Vehicle", null=True, blank=True, on_delete=models.SET_NULL, related_name="analytics_interactions")
    lead = models.ForeignKey("leads.Lead", null=True, blank=True, on_delete=models.SET_NULL, related_name="analytics_interactions")
    user = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="vehicle_interactions")
    branch = models.ForeignKey("branches.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="vehicle_interactions")
    session_hash = models.CharField(max_length=64, blank=True, db_index=True)
    ip_hash = models.CharField(max_length=64, blank=True, db_index=True)
    city = models.CharField(max_length=90, blank=True, db_index=True)
    province = models.CharField(max_length=90, blank=True, db_index=True)
    source_url = models.CharField(max_length=500, blank=True)
    referrer = models.CharField(max_length=500, blank=True)
    utm_source = models.CharField(max_length=120, blank=True, db_index=True)
    utm_medium = models.CharField(max_length=120, blank=True)
    utm_campaign = models.CharField(max_length=160, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["vehicle", "event_type", "created_at"]),
            models.Index(fields=["branch", "created_at"]),
            models.Index(fields=["city", "created_at"]),
        ]
        verbose_name = "Interacción comercial"
        verbose_name_plural = "Interacciones comerciales"

    def __str__(self):
        return f"{self.get_event_type_display()} · {self.vehicle or 'General'}"
