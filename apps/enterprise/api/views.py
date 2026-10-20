"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de configuración empresarial.

EN: This module orchestrates HTTP requests, permissions, and responses for the enterprise domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the enterprise domain.
"""

from rest_framework import viewsets
from rest_framework.permissions import BasePermission

from apps.accounts.scopes import has_global_permission
from apps.enterprise.api.serializers import ApprovalPolicySerializer, CompanyPublicSettingsSerializer
from apps.enterprise.models import ApprovalPolicy, CompanyPublicSettings
from apps.enterprise.services import update_approval_policy, update_public_settings


class EnterpriseApiPermission(BasePermission):
    def has_permission(self, request, view):
        return has_global_permission(request.user, "enterprise.manage")


class CompanyPublicSettingsViewSet(viewsets.ModelViewSet):
    serializer_class = CompanyPublicSettingsSerializer
    permission_classes = [EnterpriseApiPermission]
    http_method_names = ["get", "put", "patch", "head", "options"]
    queryset = CompanyPublicSettings.objects.select_related("company").order_by("company__commercial_name", "id")
    search_fields = ["company__commercial_name", "hero_title", "public_email"]

    def perform_update(self, serializer):
        update_public_settings(
            actor=self.request.user,
            settings=serializer.instance,
            form=serializer,
            action="enterprise.public_settings.api_update",
        )


class ApprovalPolicyViewSet(viewsets.ModelViewSet):
    serializer_class = ApprovalPolicySerializer
    permission_classes = [EnterpriseApiPermission]
    http_method_names = ["get", "put", "patch", "head", "options"]
    queryset = ApprovalPolicy.objects.select_related("company").prefetch_related("applies_to_roles").order_by("company__commercial_name", "action")
    filterset_fields = ["company", "action", "mode", "is_active"]
    search_fields = ["company__commercial_name", "notes"]

    def perform_update(self, serializer):
        update_approval_policy(actor=self.request.user, policy=serializer.instance, form=serializer)
