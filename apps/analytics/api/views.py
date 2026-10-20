"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de analítica.

EN: This module orchestrates HTTP requests, permissions, and responses for the analytics domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the analytics domain.
"""

from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet
from drf_spectacular.utils import OpenApiTypes, extend_schema

from apps.analytics.api.serializers import VehicleInteractionSerializer
from apps.analytics.forms import CommercialAnalyticsFilterForm
from apps.analytics.models import VehicleInteraction
from apps.analytics.selectors import commercial_dashboard_data, filtered_commercial_leads, filtered_interactions


def _validated_filters(request, *, permission_codes=("analytics.view",)):
    form = CommercialAnalyticsFilterForm(request.GET, user=request.user, permission_codes=permission_codes)
    if not form.is_valid():
        raise ValidationError(form.errors)
    return form.cleaned_data


class AnalyticsDatasetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 500


class VehicleInteractionViewSet(ReadOnlyModelViewSet):
    queryset = VehicleInteraction.objects.none()
    serializer_class = VehicleInteractionSerializer
    filterset_fields = ["event_type", "vehicle", "lead", "branch", "city", "utm_source"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not getattr(self.request.user, "is_authenticated", False):
            return self.queryset
        if not self.request.user.has_perm_code("analytics.view"):
            return filtered_interactions(self.request.user, {}).none()
        return filtered_interactions(self.request.user, {})


class CommercialAnalyticsSummaryAPIView(APIView):
    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        if not request.user.has_perm_code("analytics.view"):
            return Response({"detail": "No autorizado."}, status=403)
        cleaned = _validated_filters(request)
        data = commercial_dashboard_data(request.user, cleaned)
        return Response({key: value for key, value in data.items() if key not in {"recent_leads", "recent_activity"}})


class CommercialLeadDatasetAPIView(APIView):
    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        if not request.user.has_perm_code("analytics.export"):
            return Response({"detail": "No autorizado."}, status=403)
        cleaned = _validated_filters(request, permission_codes=("analytics.export",))
        paginator = AnalyticsDatasetPagination()
        rows = paginator.paginate_queryset(
            filtered_commercial_leads(request.user, cleaned, permission_codes=("analytics.export",)),
            request,
            view=self,
        )
        data = [
            {
                "lead_code": lead.code, "created_at": lead.created_at, "status": lead.status, "priority": lead.priority,
                "source": lead.source, "request_type": lead.request_type, "city": lead.city, "province": lead.province,
                "branch_id": lead.branch_id, "advisor_id": lead.assigned_advisor_id, "vehicle_id": lead.vehicle_id,
                "vehicle_code": lead.vehicle.internal_code if lead.vehicle else "", "score": lead.score,
                "customer_id": lead.customer_id, "sale_id": lead.linked_sale_id, "won": lead.status == "won",
            }
            for lead in rows
        ]
        return paginator.get_paginated_response(data)
