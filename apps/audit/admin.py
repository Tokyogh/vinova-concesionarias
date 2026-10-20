"""ES: Este módulo registra modelos en la administración de Django para el dominio de auditoría.

EN: This module registers models in Django admin for the audit domain.

Contexto existente / Existing context:
Django admin registrations for the audit domain.
"""

from django.contrib import admin

from apps.audit.models import AuditLog, SecurityAlert


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["occurred_at", "severity", "result", "user_display_snapshot", "action", "content_type_label", "object_id", "branch"]
    list_filter = ["category", "severity", "result", "is_sensitive", "occurred_at"]
    search_fields = ["event_id", "request_id", "action", "object_repr", "object_id", "username_snapshot", "ip_address"]
    readonly_fields = [field.name for field in AuditLog._meta.fields]
    date_hierarchy = "occurred_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SecurityAlert)
class SecurityAlertAdmin(admin.ModelAdmin):
    list_display = ["created_at", "severity", "status", "code", "title", "user", "branch"]
    list_filter = ["severity", "status", "created_at"]
    search_fields = ["alert_id", "code", "title", "description", "user__username"]
    readonly_fields = ["alert_id", "audit_log", "created_at", "updated_at"]
