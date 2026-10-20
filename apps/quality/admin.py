"""ES: Este módulo registra modelos en la administración de Django para el dominio de calidad.

EN: This module registers models in Django admin for the quality domain.

Contexto existente / Existing context:
Django admin registrations for the quality domain.
"""

from django.contrib import admin

from apps.quality.models import QualityCheckResult, QualityRun


class QualityCheckInline(admin.TabularInline):
    model = QualityCheckResult
    extra = 0
    readonly_fields = (
        "sequence",
        "code",
        "category",
        "title",
        "status",
        "duration_seconds",
        "message",
    )
    can_delete = False


@admin.register(QualityRun)
class QualityRunAdmin(admin.ModelAdmin):
    list_display = (
        "public_id",
        "profile",
        "status",
        "trigger",
        "requested_by",
        "passed_count",
        "failed_count",
        "created_at",
    )
    list_filter = ("profile", "status", "trigger")
    search_fields = ("public_id", "source_commit", "requested_by__email", "requested_by__username")
    readonly_fields = (
        "public_id",
        "celery_task_id",
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
        "report_json_path",
        "report_html_path",
        "summary",
        "error_message",
        "created_at",
        "updated_at",
    )
    inlines = [QualityCheckInline]
