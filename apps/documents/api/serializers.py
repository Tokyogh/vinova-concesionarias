"""ES: Este módulo serializa y valida contratos de API para el dominio de documentos.

EN: This module serializes and validates API contracts for the documents domain.

Contexto existente / Existing context:
REST serializers and API validation for the documents domain.
"""

from rest_framework import serializers

from apps.documents.models import DocumentCategory, PrivateDocument, ReusableAsset


class DocumentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentCategory
        fields = ["id", "name", "scope", "description", "is_active", "created_at", "updated_at"]


class ReusableAssetSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    uploaded_by_name = serializers.CharField(source="uploaded_by.get_full_name", read_only=True)

    class Meta:
        model = ReusableAsset
        fields = [
            "id", "title", "asset_type", "visibility", "description", "alt_text", "file_url", "file_hash", "original_name", "mime_type", "size_bytes", "extension", "branch", "branch_name", "uploaded_by", "uploaded_by_name", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["file_hash", "original_name", "mime_type", "size_bytes", "extension", "uploaded_by"]

    def get_file_url(self, obj) -> str | None:
        return obj.file.url if obj.file else None


class PrivateDocumentSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    customer_name = serializers.CharField(source="customer.display_name", read_only=True)
    vehicle_label = serializers.SerializerMethodField()
    sale_number = serializers.CharField(source="sale.number", read_only=True)
    uploaded_by_name = serializers.CharField(source="uploaded_by.get_full_name", read_only=True)

    class Meta:
        model = PrivateDocument
        fields = [
            "id", "title", "document_type", "category", "status", "branch", "branch_name", "customer", "customer_name", "vehicle", "vehicle_label", "sale", "sale_number", "notes", "expires_at", "is_confidential", "file_hash", "original_name", "mime_type", "size_bytes", "extension", "uploaded_by", "uploaded_by_name", "last_downloaded_at", "created_at", "updated_at",
        ]
        read_only_fields = ["file_hash", "original_name", "mime_type", "size_bytes", "extension", "uploaded_by", "last_downloaded_at"]

    def get_vehicle_label(self, obj) -> str:
        return str(obj.vehicle) if obj.vehicle else ""
