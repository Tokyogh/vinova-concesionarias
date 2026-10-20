"""ES: Este módulo declara el enrutamiento URL para el dominio de API e integraciones.

EN: This module declares URL routing for the api domain.

Contexto existente / Existing context:
URL routing for the api domain.
"""

from django.urls import include, path

from apps.analytics.api.views import CommercialAnalyticsSummaryAPIView, CommercialLeadDatasetAPIView
from apps.api.routing import build_router
from apps.reports.api.views import ReportDetailAPIView, ReportSummaryAPIView

router = build_router()

urlpatterns = [
    path("", include(router.urls)),
    path("reports/summary/", ReportSummaryAPIView.as_view(), name="reports-summary"),
    path("commercial-analytics/summary/", CommercialAnalyticsSummaryAPIView.as_view(), name="commercial-analytics-summary"),
    path("commercial-analytics/leads-dataset/", CommercialLeadDatasetAPIView.as_view(), name="commercial-leads-dataset"),
    path("reports/<slug:report_type>/", ReportDetailAPIView.as_view(), name="reports-detail"),
]
