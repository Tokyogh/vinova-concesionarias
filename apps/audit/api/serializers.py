"""ES: Este módulo serializa y valida contratos de API para el dominio de auditoría.

EN: This module serializes and validates API contracts for the audit domain.

Contexto existente / Existing context:
REST serializers and API validation for the audit domain.
"""

from rest_framework import serializers

from apps.audit.models import AuditLog, SecurityAlert


class AuditLogSerializer(serializers.ModelSerializer):
    user_label = serializers.CharField(source="user_display_snapshot", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "event_id", "occurred_at", "user", "user_label", "role_snapshot", "branch", "branch_name", "customer",
            "action", "category", "severity", "result", "object_repr", "content_type_label", "object_id",
            "request_id", "ip_address", "http_method", "request_path", "before", "after", "metadata",
            "is_sensitive", "previous_hash", "entry_hash",
        ]
        read_only_fields = fields


class SecurityAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityAlert
        fields = [
            "alert_id", "audit_log", "code", "title", "description", "severity", "status", "branch", "user",
            "assigned_to", "resolved_by", "resolved_at", "resolution_notes", "occurrence_count", "metadata", "created_at", "updated_at",
        ]
        read_only_fields = fields
