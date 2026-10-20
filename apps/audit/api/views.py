"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de auditoría.

EN: This module orchestrates HTTP requests, permissions, and responses for the audit domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the audit domain.
"""

from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.audit.api.serializers import AuditLogSerializer, SecurityAlertSerializer
from apps.audit.models import AuditLog, SecurityAlert
from apps.audit.selectors import scoped_alert_queryset, scoped_audit_queryset


class AuditLogViewSet(ReadOnlyModelViewSet):
    queryset = AuditLog.objects.none()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "event_id"
    filterset_fields = ["action", "category", "severity", "result", "user", "branch", "content_type_label"]
    search_fields = ["action", "object_repr", "object_id", "username_snapshot", "ip_address", "request_path"]
    ordering_fields = ["occurred_at", "severity", "action"]
    ordering = ["-occurred_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not getattr(self.request.user, "is_authenticated", False):
            return self.queryset
        if not self.request.user.has_perm_code("audit.view"):
            return scoped_audit_queryset(self.request.user).none()
        return scoped_audit_queryset(self.request.user)


class SecurityAlertViewSet(ReadOnlyModelViewSet):
    queryset = SecurityAlert.objects.none()
    serializer_class = SecurityAlertSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "alert_id"
    filterset_fields = ["code", "severity", "status", "branch", "user"]
    search_fields = ["code", "title", "description", "user__username"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not getattr(self.request.user, "is_authenticated", False):
            return self.queryset
        if not self.request.user.has_perm_code("audit.view"):
            return scoped_alert_queryset(self.request.user).none()
        return scoped_alert_queryset(self.request.user)
