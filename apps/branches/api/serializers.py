"""ES: Este módulo serializa y valida contratos de API para el dominio de sucursales.

EN: This module serializes and validates API contracts for the branches domain.

Contexto existente / Existing context:
Serializadores REST y validación API para sedes.

REST serializers and API validation for the branches domain.
"""

from rest_framework import serializers
from apps.branches.models import Branch
from apps.common.validators import (
    validate_human_name,
    validate_no_unsafe_control_characters,
    validate_phone_number,
)


class BranchSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.commercial_name", read_only=True)
    user_count = serializers.IntegerField(read_only=True)
    vehicle_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Branch
        fields = [
            "id",
            "company",
            "company_name",
            "name",
            "code",
            "branch_type",
            "city",
            "province",
            "address",
            "phone",
            "email",
            "description",
            "opening_hours",
            "services",
            "photo",
            "website_url",
            "latitude",
            "longitude",
            "is_public",
            "is_active",
            "user_count",
            "vehicle_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "name": {"validators": [validate_no_unsafe_control_characters]},
            "city": {"validators": [validate_human_name]},
            "province": {"validators": [validate_human_name]},
            "address": {"validators": [validate_no_unsafe_control_characters]},
            "phone": {"validators": [validate_phone_number]},
            "description": {"validators": [validate_no_unsafe_control_characters]},
            "opening_hours": {"validators": [validate_no_unsafe_control_characters]},
        }

    def validate_services(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Los servicios deben enviarse como una lista.")
        normalized = []
        for item in value:
            service = str(item).strip()
            if service and service not in normalized:
                normalized.append(service[:80])
        return normalized[:12]
