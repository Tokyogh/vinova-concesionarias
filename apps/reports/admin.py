"""ES: Este módulo registra modelos en la administración de Django para el dominio de reportes.

EN: This module registers models in Django admin for the reports domain.

Contexto existente / Existing context:
Django admin registrations for the reports domain.
"""

from django.contrib import admin

from apps.reports.models import ReportExportJob


@admin.register(ReportExportJob)
class ReportExportJobAdmin(admin.ModelAdmin):
    list_display = ("report_type", "export_format", "status", "requested_by", "row_count", "created_at", "completed_at")
    list_filter = ("report_type", "export_format", "status", "created_at")
    search_fields = ("file_name", "requested_by__username", "requested_by__email")
    readonly_fields = ("created_at", "updated_at", "completed_at")
