"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de importaciones.

EN: This module orchestrates HTTP requests, permissions, and responses for the imports domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the imports domain.
"""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.imports.api.serializers import ImportBatchSerializer, ImportRowSerializer
from apps.imports.models import ImportRow
from apps.imports.permissions import CanManageImports
from apps.imports.selectors import import_batch_queryset


class ImportBatchViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ImportBatchSerializer
    permission_classes = [CanManageImports]
    filterset_fields = ["import_type", "status"]
    search_fields = ["original_filename", "file_hash", "uploaded_by__username", "uploaded_by__email"]
    ordering_fields = ["created_at", "total_rows", "created_count", "updated_count", "error_count"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return import_batch_queryset(user=self.request.user).prefetch_related("rows")

    @action(detail=True, methods=["get"])
    def rows(self, request, pk=None):
        batch = self.get_object()
        serializer = ImportRowSerializer(batch.rows.all()[:500], many=True)
        return Response(serializer.data)


class ImportRowViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ImportRowSerializer
    permission_classes = [CanManageImports]
    filterset_fields = ["batch", "status", "action"]
    ordering_fields = ["row_number", "created_at"]
    ordering = ["row_number"]

    def get_queryset(self):
        return ImportRow.objects.select_related("batch").filter(batch__in=import_batch_queryset(user=self.request.user))
