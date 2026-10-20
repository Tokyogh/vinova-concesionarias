"""ES: Este módulo registra modelos en la administración de Django para el dominio de continuidad.

EN: This module registers models in Django admin for the continuity domain.

Contexto existente / Existing context:
Django admin registrations for the continuity domain.
"""

from django.contrib import admin

from apps.continuity.models import BackupPolicy, BackupRecord, RestoreDrill


@admin.register(BackupPolicy)
class BackupPolicyAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "frequency", "retention_days", "last_success_at")


@admin.register(BackupRecord)
class BackupRecordAdmin(admin.ModelAdmin):
    list_display = ("public_id", "backup_type", "status", "execution_mode", "size_bytes", "created_at", "initiated_by")
    list_filter = ("backup_type", "status", "execution_mode")
    readonly_fields = ("public_id", "sha256", "manifest", "archive_path", "size_bytes", "celery_task_id", "queue_error")


@admin.register(RestoreDrill)
class RestoreDrillAdmin(admin.ModelAdmin):
    list_display = ("public_id", "backup", "status", "environment", "created_at", "performed_by")
    list_filter = ("status",)
