"""ES: Este módulo serializa y valida contratos de API para el dominio de configuración empresarial.

EN: This module serializes and validates API contracts for the enterprise domain.

Contexto existente / Existing context:
REST serializers and API validation for the enterprise domain.
"""

from rest_framework import serializers

from apps.common.validators import validate_no_unsafe_control_characters, validate_phone_number
from apps.enterprise.models import ApprovalPolicy, CompanyPublicSettings


class CompanyPublicSettingsSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.commercial_name", read_only=True)

    class Meta:
        model = CompanyPublicSettings
        fields = [
            "id",
            "company",
            "company_name",
            "website",
            "whatsapp",
            "public_email",
            "public_phone",
            "public_address",
            "opening_hours",
            "hero_title",
            "hero_subtitle",
            "catalog_intro_title",
            "footer_text",
            "show_public_branches",
            "show_vehicle_prices",
            "allow_client_registration",
            "updated_at",
        ]
        read_only_fields = ["company", "company_name", "updated_at"]
        extra_kwargs = {
            "whatsapp": {"validators": [validate_phone_number]},
            "public_phone": {"validators": [validate_phone_number]},
            "public_address": {"validators": [validate_no_unsafe_control_characters]},
            "opening_hours": {"validators": [validate_no_unsafe_control_characters]},
        }


class ApprovalPolicySerializer(serializers.ModelSerializer):
    action_label = serializers.CharField(source="get_action_display", read_only=True)
    mode_label = serializers.CharField(source="get_mode_display", read_only=True)

    class Meta:
        model = ApprovalPolicy
        fields = [
            "id",
            "company",
            "action",
            "action_label",
            "mode",
            "mode_label",
            "threshold_amount",
            "threshold_percent",
            "applies_to_roles",
            "requires_reason",
            "notify_supervisors",
            "is_active",
            "notes",
        ]
        read_only_fields = ["company", "action"]
