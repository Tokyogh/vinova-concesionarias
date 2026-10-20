"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de configuración SRI heredada.

EN: This module orchestrates HTTP requests, permissions, and responses for the sri integration domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the sri integration domain.
"""

from rest_framework.permissions import BasePermission
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.accounts.scopes import has_global_permission
from apps.sri_integration.api.serializers import SriConfigurationSerializer, SriEstablishmentSerializer, SriSequenceSerializer
from apps.sri_integration.models import SriConfiguration, SriEstablishment, SriSequence


class SriApiPermission(BasePermission):
    def has_permission(self, request, view):
        return has_global_permission(request.user, "sri.manage")


class SriConfigurationViewSet(ReadOnlyModelViewSet):
    serializer_class = SriConfigurationSerializer
    permission_classes = [SriApiPermission]
    queryset = SriConfiguration.objects.select_related("company").order_by("company__commercial_name", "id")
    filterset_fields = ["environment", "status"]
    search_fields = ["ruc", "legal_name", "company__commercial_name"]


class SriEstablishmentViewSet(ReadOnlyModelViewSet):
    serializer_class = SriEstablishmentSerializer
    permission_classes = [SriApiPermission]
    queryset = SriEstablishment.objects.select_related("configuration", "branch").order_by("configuration__company__commercial_name", "establishment_code", "emission_point_code")
    filterset_fields = ["configuration", "is_active", "is_default"]
    search_fields = ["establishment_code", "emission_point_code", "name"]


class SriSequenceViewSet(ReadOnlyModelViewSet):
    serializer_class = SriSequenceSerializer
    permission_classes = [SriApiPermission]
    queryset = SriSequence.objects.select_related("establishment").order_by("establishment__establishment_code", "establishment__emission_point_code", "document_type")
    filterset_fields = ["document_type", "is_active", "establishment"]
