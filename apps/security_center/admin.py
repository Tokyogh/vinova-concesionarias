"""ES: Este módulo registra modelos en la administración de Django para el dominio de seguridad.

EN: This module registers models in Django admin for the security center domain.

Contexto existente / Existing context:
Django admin registrations for the security center domain.
"""

from django.contrib import admin
from apps.security_center.models import ActiveSession, PasswordHistory, SecurityPolicy, StaffAccessRequest, UserSecurityProfile

@admin.register(SecurityPolicy)
class SecurityPolicyAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "min_password_length", "password_max_age_days", "session_idle_minutes")

@admin.register(UserSecurityProfile)
class UserSecurityProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "two_factor_enabled", "two_factor_confirmed_at", "last_two_factor_at")
    readonly_fields = ("encrypted_totp_secret", "backup_code_hashes")

@admin.register(ActiveSession)
class ActiveSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "session_reference", "last_seen_at", "revoked_at")
    search_fields = ("user__username", "user__email")

    @admin.display(description="Referencia")
    def session_reference(self, obj):
        import hashlib
        return hashlib.sha256(obj.session_key.encode("utf-8")).hexdigest()[:12]

@admin.register(PasswordHistory)
class PasswordHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at")
    readonly_fields = ("encoded_password",)


@admin.register(StaffAccessRequest)
class StaffAccessRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "created_at", "access_expires_at", "decided_by")
    list_filter = ("status",)
    search_fields = ("user__username", "user__email")
    readonly_fields = (
        "user", "session_reference", "ip_hash", "user_agent_hash", "risk_reasons",
        "status", "request_expires_at", "access_expires_at", "decided_by", "decided_at",
        "decision_note", "created_at", "updated_at",
    )
