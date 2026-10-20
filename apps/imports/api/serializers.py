"""ES: Este módulo serializa y valida contratos de API para el dominio de importaciones.

EN: This module serializes and validates API contracts for the imports domain.

Contexto existente / Existing context:
REST serializers and API validation for the imports domain.
"""

from rest_framework import serializers

from apps.imports.models import ImportBatch, ImportRow


class ImportRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportRow
        fields = ["id", "row_number", "status", "payload", "normalized_payload", "errors", "action", "object_label", "object_id"]
        read_only_fields = fields


class ImportBatchSerializer(serializers.ModelSerializer):
    uploaded_by_label = serializers.CharField(source="uploaded_by.get_username", read_only=True)
    default_branch_label = serializers.CharField(source="default_branch.name", read_only=True)
    rows = ImportRowSerializer(many=True, read_only=True)

    class Meta:
        model = ImportBatch
        fields = [
            "id",
            "import_type",
            "status",
            "original_filename",
            "file_hash",
            "file_size",
            "uploaded_by",
            "uploaded_by_label",
            "confirmed_by",
            "default_branch",
            "default_branch_label",
            "require_vehicle_branch",
            "total_rows",
            "valid_rows",
            "invalid_rows",
            "created_count",
            "updated_count",
            "skipped_count",
            "error_count",
            "preview_rows",
            "errors",
            "result_summary",
            "notes",
            "validated_at",
            "confirmed_at",
            "completed_at",
            "created_at",
            "updated_at",
            "rows",
        ]
        read_only_fields = fields
