"""ES: Este módulo serializa y valida contratos de API para el dominio de continuidad.

EN: This module serializes and validates API contracts for the continuity domain.

Contexto existente / Existing context:
REST serializers and API validation for the continuity domain.
"""

from rest_framework import serializers

from apps.continuity.models import BackupPolicy, BackupRecord, RestoreDrill


class BackupPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupPolicy
        fields = [
            "id",
            "name",
            "is_active",
            "frequency",
            "retention_days",
            "include_database",
            "include_media",
            "include_private",
            "external_copy_required",
            "destination_hint",
            "last_success_at",
            "next_review_at",
        ]
        read_only_fields = fields


class BackupRecordSerializer(serializers.ModelSerializer):
    size_display = serializers.CharField(read_only=True)

    class Meta:
        model = BackupRecord
        fields = [
            "public_id",
            "backup_type",
            "status",
            "execution_mode",
            "queued_at",
            "celery_task_id",
            "filename",
            "size_bytes",
            "size_display",
            "sha256",
            "manifest",
            "started_at",
            "completed_at",
            "verified_at",
            "created_at",
            "queue_error",
            "error_message",
        ]
        read_only_fields = fields


class RestoreDrillSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestoreDrill
        fields = [
            "public_id",
            "backup",
            "status",
            "environment",
            "planned_at",
            "started_at",
            "completed_at",
            "checklist",
            "result_summary",
            "evidence_hash",
            "created_at",
        ]
        read_only_fields = fields
