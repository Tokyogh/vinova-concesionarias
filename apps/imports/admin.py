"""ES: Este módulo registra modelos en la administración de Django para el dominio de importaciones.

EN: This module registers models in Django admin for the imports domain.

Contexto existente / Existing context:
Django admin registrations for the imports domain.
"""

from django.contrib import admin

from apps.imports.models import ImportBatch, ImportRow


class ImportRowInline(admin.TabularInline):
    model = ImportRow
    extra = 0
    readonly_fields = ("row_number", "status", "action", "object_label", "object_id", "errors")
    fields = ("row_number", "status", "action", "object_label", "object_id", "errors")
    can_delete = False


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = ("import_type", "status", "original_filename", "uploaded_by", "default_branch", "total_rows", "created_count", "updated_count", "error_count", "created_at")
    list_filter = ("import_type", "status", "default_branch", "require_vehicle_branch", "created_at")
    search_fields = ("original_filename", "file_hash", "uploaded_by__username", "uploaded_by__email")
    readonly_fields = ("file_hash", "file_size", "total_rows", "valid_rows", "invalid_rows", "created_count", "updated_count", "skipped_count", "error_count", "preview_rows", "errors", "result_summary", "validated_at", "confirmed_at", "completed_at", "created_at", "updated_at")
    inlines = [ImportRowInline]


@admin.register(ImportRow)
class ImportRowAdmin(admin.ModelAdmin):
    list_display = ("batch", "row_number", "status", "action", "object_label", "object_id")
    list_filter = ("status", "action", "batch__import_type")
    search_fields = ("batch__original_filename", "object_id", "object_label")
