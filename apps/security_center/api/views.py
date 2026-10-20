"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de seguridad.

EN: This module orchestrates HTTP requests, permissions, and responses for the security center domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the security center domain.
"""

from rest_framework import viewsets
from rest_framework.permissions import BasePermission

from apps.security_center.api.serializers import ActiveSessionSerializer, SecurityPolicySerializer
from apps.security_center.models import ActiveSession, SecurityPolicy
from apps.security_center.selectors import active_sessions_queryset

class SecurityPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.has_perm_code("security.view"))

class SecurityPolicyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SecurityPolicySerializer
    permission_classes = [SecurityPermission]
    queryset = SecurityPolicy.objects.all()

class ActiveSessionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActiveSessionSerializer
    permission_classes = [SecurityPermission]
    queryset = ActiveSession.objects.select_related("user").all()
    filterset_fields = ["user", "revoked_at"]
    search_fields = ["user__username", "user__email", "user_agent"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not getattr(self.request.user, "is_authenticated", False):
            return self.queryset.none()
        return active_sessions_queryset(user=self.request.user)
