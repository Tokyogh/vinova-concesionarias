"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de reportes.

EN: This module orchestrates HTTP requests, permissions, and responses for the reports domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the reports domain.
"""

from __future__ import annotations

from django.utils import timezone
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiTypes, extend_schema

from apps.reports.api.serializers import ReportFilterSerializer
from apps.reports.permissions import CanViewReports
from apps.reports.services import REPORT_LABELS, get_report_context, rows_for_report


def _filters_from_request(request):
    today = timezone.localdate()
    serializer = ReportFilterSerializer(data=request.query_params, context={"request": request})
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    return {
        "start_date": data.get("start_date", today.replace(day=1)),
        "end_date": data.get("end_date", today),
        "branch": data.get("branch"),
        "seller": data.get("seller"),
        "sale_status": data.get("sale_status", ""),
        "vehicle": data.get("vehicle"),
        "category": data.get("category"),
        "q": data.get("q", "").strip(),
        "page": data.get("page", 1),
        "page_size": data.get("page_size", 50),
    }


class ReportSummaryAPIView(APIView):
    permission_classes = [CanViewReports]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        filters = _filters_from_request(request)
        return Response(get_report_context("executive", filters, request.user)["metrics"])


class ReportDetailAPIView(APIView):
    permission_classes = [CanViewReports]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request, report_type):
        if report_type not in REPORT_LABELS or report_type == "executive":
            raise NotFound("Reporte no encontrado.")
        filters = _filters_from_request(request)
        page = filters.pop("page")
        page_size = filters.pop("page_size")
        title, headers, rows = rows_for_report(
            report_type,
            filters,
            request.user,
            limit=page_size + 1,
            offset=(page - 1) * page_size,
        )
        return Response(
            {
                "title": title,
                "headers": headers,
                "rows": rows[:page_size],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "has_next": len(rows) > page_size,
                },
            }
        )
