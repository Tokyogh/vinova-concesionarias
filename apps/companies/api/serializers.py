"""ES: Este módulo serializa y valida contratos de API para el dominio de empresa.

EN: This module serializes and validates API contracts for the companies domain.

Contexto existente / Existing context:
REST serializers and API validation for the companies domain.
"""

from rest_framework import serializers
from apps.companies.models import Company
from apps.common.validators import (
    validate_ec_ruc,
    validate_hex_color,
    validate_no_unsafe_control_characters,
    validate_phone_number,
)


class CompanySerializer(serializers.ModelSerializer):
    branch_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Company
        fields = [
            "id",
            "legal_name",
            "commercial_name",
            "ruc",
            "email",
            "phone",
            "address",
            "primary_color",
            "secondary_color",
            "is_active",
            "branch_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "legal_name": {"validators": [validate_no_unsafe_control_characters]},
            "commercial_name": {"validators": [validate_no_unsafe_control_characters]},
            "ruc": {"validators": [validate_ec_ruc]},
            "phone": {"validators": [validate_phone_number]},
            "address": {"validators": [validate_no_unsafe_control_characters]},
            "primary_color": {"validators": [validate_hex_color]},
            "secondary_color": {"validators": [validate_hex_color]},
        }
