"""ES: Este módulo serializa y valida contratos de API para el dominio de privacidad.

EN: This module serializes and validates API contracts for the privacy domain.

Contexto existente / Existing context:
REST serializers and API validation for the privacy domain.
"""

from rest_framework import serializers

from apps.privacy.models import ConsentRecord, DataExportJob, DataSubjectRequest, RetentionPolicy


class ConsentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentRecord
        fields = ["public_id", "customer", "lead", "purpose", "status", "notice_version", "lawful_basis", "source", "accepted_at", "revoked_at", "created_at"]
        read_only_fields = fields


class DataSubjectRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSubjectRequest
        fields = ["public_id", "request_type", "status", "customer", "requester_name", "requester_email", "requester_phone", "description", "received_at", "due_at", "identity_verified_at", "resolution", "legal_hold_reason", "completed_at", "created_at"]
        read_only_fields = fields


class DataExportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataExportJob
        fields = ["public_id", "request", "customer", "status", "filename", "sha256", "size_bytes", "completed_at", "expires_at", "created_at", "error_message"]
        read_only_fields = fields


class RetentionPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = RetentionPolicy
        fields = ["id", "code", "name", "data_category", "retention_days", "action", "is_active", "requires_legal_review", "description", "last_review_at", "next_review_at"]
        read_only_fields = fields
