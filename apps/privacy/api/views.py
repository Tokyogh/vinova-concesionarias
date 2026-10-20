"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de privacidad.

EN: This module orchestrates HTTP requests, permissions, and responses for the privacy domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the privacy domain.
"""

from rest_framework.permissions import BasePermission
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.accounts.scopes import has_global_permission
from apps.privacy.api.serializers import ConsentRecordSerializer, DataExportJobSerializer, DataSubjectRequestSerializer, RetentionPolicySerializer
from apps.privacy.models import ConsentRecord, DataExportJob, DataSubjectRequest, RetentionPolicy
from apps.privacy.selectors import (
    scoped_consent_queryset,
    scoped_data_request_queryset,
    scoped_export_job_queryset,
    scoped_retention_policy_queryset,
)


class PrivacyPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.has_perm_code("privacy.view"))


class GlobalPrivacyPermission(BasePermission):
    def has_permission(self, request, view):
        return has_global_permission(request.user, "privacy.view")


class ConsentRecordViewSet(ReadOnlyModelViewSet):
    queryset = ConsentRecord.objects.select_related("customer", "lead", "captured_by")
    serializer_class = ConsentRecordSerializer
    permission_classes = [PrivacyPermission]
    lookup_field = "public_id"
    filterset_fields = ["purpose", "status"]
    search_fields = ["subject_name", "subject_email"]

    def get_queryset(self):
        return scoped_consent_queryset(self.request.user)


class DataSubjectRequestViewSet(ReadOnlyModelViewSet):
    queryset = DataSubjectRequest.objects.select_related("customer", "assigned_to", "identity_verified_by")
    serializer_class = DataSubjectRequestSerializer
    permission_classes = [PrivacyPermission]
    lookup_field = "public_id"
    filterset_fields = ["request_type", "status"]
    search_fields = ["requester_name", "requester_email", "requester_phone"]

    def get_queryset(self):
        return scoped_data_request_queryset(self.request.user)


class DataExportJobViewSet(ReadOnlyModelViewSet):
    queryset = DataExportJob.objects.select_related("request", "customer", "generated_by")
    serializer_class = DataExportJobSerializer
    permission_classes = [PrivacyPermission]
    lookup_field = "public_id"
    filterset_fields = ["status"]

    def get_queryset(self):
        return scoped_export_job_queryset(self.request.user)


class RetentionPolicyViewSet(ReadOnlyModelViewSet):
    queryset = RetentionPolicy.objects.all()
    serializer_class = RetentionPolicySerializer
    permission_classes = [GlobalPrivacyPermission]
    filterset_fields = ["is_active", "action"]

    def get_queryset(self):
        return scoped_retention_policy_queryset(self.request.user)
