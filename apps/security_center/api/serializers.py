"""ES: Este módulo serializa y valida contratos de API para el dominio de seguridad.

EN: This module serializes and validates API contracts for the security center domain.

Contexto existente / Existing context:
REST serializers and API validation for the security center domain.
"""

import hashlib

from rest_framework import serializers

from apps.security_center.models import ActiveSession, SecurityPolicy


class SecurityPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityPolicy
        fields = [
            "id", "name", "is_active", "min_password_length", "require_uppercase", "require_lowercase",
            "require_digit", "require_symbol", "password_max_age_days", "password_history_count",
            "session_idle_minutes", "max_active_sessions", "login_attempts_per_ip", "login_window_minutes",
            "require_2fa_for_superusers", "require_2fa_for_admin_roles", "admin_role_level_threshold",
            "staff_access_mode", "staff_access_approval_minutes",
            "staff_access_request_minutes",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class ActiveSessionSerializer(serializers.ModelSerializer):
    user_display = serializers.CharField(source="user.get_full_name", read_only=True)
    session_reference = serializers.SerializerMethodField()
    ip_reference = serializers.SerializerMethodField()

    class Meta:
        model = ActiveSession
        fields = [
            "id", "user", "user_display", "session_reference", "ip_reference", "user_agent",
            "created_at", "last_seen_at", "two_factor_verified_at", "revoked_at", "revoke_reason",
        ]
        read_only_fields = fields

    def get_session_reference(self, obj) -> str:
        return hashlib.sha256(obj.session_key.encode("utf-8")).hexdigest()[:12]

    def get_ip_reference(self, obj) -> str:
        return (obj.ip_hash or "")[:12]
