"""ES: Este módulo serializa y valida contratos de API para el dominio de configuración SRI heredada.

EN: This module serializes and validates API contracts for the sri integration domain.

Contexto existente / Existing context:
REST serializers and API validation for the sri integration domain.
"""

from rest_framework import serializers

from apps.sri_integration.models import SriConfiguration, SriEstablishment, SriSequence


class SriConfigurationSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.commercial_name", read_only=True)
    certificate_configured = serializers.SerializerMethodField()

    class Meta:
        model = SriConfiguration
        fields = [
            "id",
            "company",
            "company_name",
            "ruc",
            "legal_name",
            "commercial_name",
            "environment",
            "status",
            "accounting_required",
            "special_taxpayer_resolution",
            "withholding_agent_resolution",
            "taxpayer_regime",
            "certificate_configured",
            "certificate_expires_at",
            "technical_contact_name",
            "technical_contact_email",
            "updated_at",
        ]
        read_only_fields = ["company_name", "certificate_configured", "updated_at"]

    def get_certificate_configured(self, obj) -> bool:
        return bool(obj.certificate_file)


class SriEstablishmentSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = SriEstablishment
        fields = ["id", "configuration", "establishment_code", "emission_point_code", "name", "address", "branch", "branch_name", "is_default", "is_active"]


class SriSequenceSerializer(serializers.ModelSerializer):
    next_number_preview = serializers.CharField(read_only=True)
    establishment_label = serializers.CharField(source="establishment.__str__", read_only=True)

    class Meta:
        model = SriSequence
        fields = ["id", "establishment", "establishment_label", "document_type", "current_number", "start_number", "max_number", "next_number_preview", "is_active", "notes"]
