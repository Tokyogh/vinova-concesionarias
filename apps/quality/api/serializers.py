"""ES: Este módulo serializa y valida contratos de API para el dominio de calidad.

EN: This module serializes and validates API contracts for the quality domain.

Contexto existente / Existing context:
REST serializers and API validation for the quality domain.
"""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.quality.models import QualityCheckResult, QualityRun


class QualityCheckResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualityCheckResult
        fields = ("sequence", "code", "category", "title", "status", "duration_seconds", "message")


class QualityRunListSerializer(serializers.ModelSerializer):
    requested_by = serializers.SerializerMethodField()
    release_ready = serializers.BooleanField(read_only=True)

    class Meta:
        model = QualityRun
        fields = (
            "public_id",
            "profile",
            "status",
            "trigger",
            "requested_by",
            "source_version",
            "source_commit",
            "environment_name",
            "started_at",
            "completed_at",
            "duration_seconds",
            "passed_count",
            "warning_count",
            "failed_count",
            "skipped_count",
            "release_ready",
            "created_at",
        )

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_requested_by(self, obj) -> str | None:
        if not obj.requested_by:
            return None
        return obj.requested_by.get_full_name().strip() or obj.requested_by.username


class QualityRunSerializer(QualityRunListSerializer):
    summary = serializers.JSONField(read_only=True)
    checks = QualityCheckResultSerializer(many=True, read_only=True)

    class Meta(QualityRunListSerializer.Meta):
        fields = (*QualityRunListSerializer.Meta.fields, "summary", "checks")


class QualityRunCreateSerializer(serializers.Serializer):
    profile = serializers.ChoiceField(choices=QualityRun.Profile.choices)
