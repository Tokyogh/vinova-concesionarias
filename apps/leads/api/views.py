"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de CRM y leads.

EN: This module orchestrates HTTP requests, permissions, and responses for the leads domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the leads domain.
"""

from rest_framework import mixins
from rest_framework.permissions import BasePermission
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.leads.api.serializers import LeadActivitySerializer, LeadSerializer, TestDriveSerializer
from apps.leads.models import Lead, LeadActivity, TestDrive
from apps.leads.selectors import scoped_lead_queryset


class LeadsApiPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return user.has_perm_code("leads.view")
        return user.has_perm_code("leads.manage")


class CreateReadOnlyModelViewSet(mixins.CreateModelMixin, ReadOnlyModelViewSet):
    pass


class LeadViewSet(ModelViewSet):
    queryset = Lead.objects.none()
    serializer_class = LeadSerializer
    permission_classes = [LeadsApiPermission]
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["status", "priority", "source", "request_type", "branch", "assigned_advisor", "vehicle", "city"]
    search_fields = ["code", "full_name", "email", "phone", "whatsapp", "city", "vehicle__internal_code", "vehicle__brand__name", "vehicle__model__name"]
    ordering_fields = ["created_at", "updated_at", "score", "next_follow_up_at", "status"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not getattr(self.request.user, "is_authenticated", False):
            return self.queryset
        if not self.request.user.has_perm_code("leads.view"):
            return scoped_lead_queryset(self.request.user).none()
        return scoped_lead_queryset(self.request.user)

    def perform_create(self, serializer):
        serializer.save()


class LeadActivityViewSet(CreateReadOnlyModelViewSet):
    queryset = LeadActivity.objects.none()
    serializer_class = LeadActivitySerializer
    permission_classes = [LeadsApiPermission]
    filterset_fields = ["lead", "activity_type", "created_by"]
    ordering_fields = ["created_at", "scheduled_for", "completed_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not getattr(self.request.user, "is_authenticated", False):
            return self.queryset
        lead_ids = scoped_lead_queryset(self.request.user).values_list("id", flat=True)
        return LeadActivity.objects.filter(lead_id__in=lead_ids).select_related("lead", "created_by")

    def perform_create(self, serializer):
        serializer.save()


class TestDriveViewSet(CreateReadOnlyModelViewSet):
    queryset = TestDrive.objects.none()
    serializer_class = TestDriveSerializer
    permission_classes = [LeadsApiPermission]
    filterset_fields = ["lead", "vehicle", "branch", "advisor", "status"]
    ordering_fields = ["starts_at", "created_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not getattr(self.request.user, "is_authenticated", False):
            return self.queryset
        lead_ids = scoped_lead_queryset(self.request.user).values_list("id", flat=True)
        return TestDrive.objects.filter(lead_id__in=lead_ids).select_related("lead", "vehicle", "branch", "advisor")

    def perform_create(self, serializer):
        serializer.save()
