"""ES: Este módulo serializa y valida contratos de API para el dominio de analítica.

EN: This module serializes and validates API contracts for the analytics domain.

Contexto existente / Existing context:
REST serializers and API validation for the analytics domain.
"""

from rest_framework import serializers

from apps.analytics.models import VehicleInteraction


class VehicleInteractionSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)

    class Meta:
        model = VehicleInteraction
        fields = [
            "event_id", "event_type", "event_type_display", "vehicle", "lead", "user", "branch", "city", "province",
            "utm_source", "utm_medium", "utm_campaign", "metadata", "created_at",
        ]
        read_only_fields = fields
