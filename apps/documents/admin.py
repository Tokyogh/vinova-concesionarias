"""ES: Este módulo registra modelos en la administración de Django para el dominio de documentos.

EN: This module registers models in Django admin for the documents domain.

Contexto existente / Existing context:
Django admin registrations for the documents domain.
"""

from django.contrib import admin

from apps.documents.models import DocumentCategory, PrivateDocument, ReusableAsset


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "scope", "is_active", "created_at")
    list_filter = ("scope", "is_active")
    search_fields = ("name", "description")


@admin.register(ReusableAsset)
class ReusableAssetAdmin(admin.ModelAdmin):
    list_display = ("title", "asset_type", "visibility", "branch", "is_active", "size_bytes", "created_at")
    list_filter = ("asset_type", "visibility", "is_active", "branch")
    search_fields = ("title", "original_name", "file_hash", "description")
    readonly_fields = ("file_hash", "original_name", "mime_type", "size_bytes", "extension", "uploaded_by")


@admin.register(PrivateDocument)
class PrivateDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "document_type", "status", "branch", "customer", "vehicle", "is_confidential", "created_at")
    list_filter = ("document_type", "status", "branch", "is_confidential")
    search_fields = ("title", "original_name", "file_hash", "customer__first_name", "customer__last_name", "customer__business_name", "vehicle__vin", "vehicle__plate")
    readonly_fields = ("file_hash", "original_name", "mime_type", "size_bytes", "extension", "uploaded_by", "last_downloaded_at")
