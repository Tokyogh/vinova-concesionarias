"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de continuidad.

EN: This module orchestrates HTTP requests, permissions, and responses for the continuity domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the continuity domain.
"""

from rest_framework.permissions import BasePermission
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.accounts.scopes import has_global_permission
from apps.continuity.api.serializers import BackupPolicySerializer, BackupRecordSerializer, RestoreDrillSerializer
from apps.continuity.models import BackupPolicy, BackupRecord, RestoreDrill


class ContinuityPermission(BasePermission):
    def has_permission(self, request, view):
        return has_global_permission(request.user, "continuity.view")


class BackupPolicyViewSet(ReadOnlyModelViewSet):
    queryset = BackupPolicy.objects.all()
    serializer_class = BackupPolicySerializer
    permission_classes = [ContinuityPermission]


class BackupRecordViewSet(ReadOnlyModelViewSet):
    queryset = BackupRecord.objects.select_related("policy", "initiated_by", "verified_by")
    serializer_class = BackupRecordSerializer
    permission_classes = [ContinuityPermission]
    lookup_field = "public_id"
    search_fields = ["filename", "sha256", "notes"]
    filterset_fields = ["backup_type", "status"]
    ordering_fields = ["created_at", "completed_at", "size_bytes"]


class RestoreDrillViewSet(ReadOnlyModelViewSet):
    queryset = RestoreDrill.objects.select_related("backup", "performed_by")
    serializer_class = RestoreDrillSerializer
    permission_classes = [ContinuityPermission]
    lookup_field = "public_id"
    filterset_fields = ["status"]
