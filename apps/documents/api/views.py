"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de documentos.

EN: This module orchestrates HTTP requests, permissions, and responses for the documents domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the documents domain.
"""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from apps.documents.api.serializers import DocumentCategorySerializer, PrivateDocumentSerializer, ReusableAssetSerializer
from apps.documents.models import DocumentCategory, PrivateDocument, ReusableAsset
from apps.documents.selectors import document_dashboard_metrics, private_documents_queryset, reusable_assets_queryset


class DocumentPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return request.user.has_perm_code("documents.view") or request.user.has_perm_code("documents.manage") or request.user.has_perm_code("documents.download_private")
        return request.user.has_perm_code("documents.manage")


class DocumentCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentCategorySerializer
    permission_classes = [DocumentPermission]
    queryset = DocumentCategory.objects.all().order_by("scope", "name")
    filterset_fields = ["scope", "is_active"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "scope", "created_at"]


class ReusableAssetViewSet(viewsets.ModelViewSet):
    serializer_class = ReusableAssetSerializer
    permission_classes = [DocumentPermission]
    queryset = ReusableAsset.objects.none()

    def get_queryset(self):
        return reusable_assets_queryset(user=self.request.user)
    filterset_fields = ["asset_type", "visibility", "is_active", "branch"]
    search_fields = ["title", "description", "original_name", "file_hash"]
    ordering_fields = ["title", "created_at", "size_bytes"]

    @action(detail=False, methods=["get"], url_path="metrics")
    def metrics(self, request):
        return Response(document_dashboard_metrics(user=request.user))


class PrivateDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PrivateDocumentSerializer
    permission_classes = [DocumentPermission]
    queryset = PrivateDocument.objects.none()

    def get_queryset(self):
        return private_documents_queryset(user=self.request.user)
    filterset_fields = ["document_type", "status", "branch", "customer", "vehicle", "sale", "is_confidential"]
    search_fields = ["title", "notes", "original_name", "file_hash", "customer__first_name", "customer__last_name", "customer__business_name", "vehicle__vin", "vehicle__plate", "sale__number"]
    ordering_fields = ["title", "created_at", "expires_at", "size_bytes"]

    @action(detail=False, methods=["get"], url_path="metrics")
    def metrics(self, request):
        return Response(document_dashboard_metrics(user=request.user))
