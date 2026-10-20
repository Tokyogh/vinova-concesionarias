"""ES: Este módulo implementa el componente v1 urls para el dominio de API e integraciones.

EN: This module implements the v1 urls component for the api domain.

Contexto existente / Existing context:
V1 urls support for the api domain.
"""

from django.urls import include, path

from apps.analytics.api.views import CommercialAnalyticsSummaryAPIView, CommercialLeadDatasetAPIView
from apps.api.routing import build_router
from apps.api.views import (
    AccountingExportAPIView,
    APIMetadataAPIView,
    BIDatasetAPIView,
    BIDatasetCatalogAPIView,
    ExternalLeadIngestAPIView,
)
from apps.reports.api.views import ReportDetailAPIView, ReportSummaryAPIView

app_name = "api_v1"
router = build_router()

urlpatterns = [
    path("quality/", include("apps.quality.api.urls")),
    path("", include(router.urls)),
    path("meta/", APIMetadataAPIView.as_view(), name="meta"),
    path("integrations/leads/", ExternalLeadIngestAPIView.as_view(), name="integration-lead-ingest"),
    path("integrations/accounting/export/", AccountingExportAPIView.as_view(), name="accounting-export"),
    path("bi/", BIDatasetCatalogAPIView.as_view(), name="bi-catalog"),
    path("bi/<slug:dataset>/", BIDatasetAPIView.as_view(), name="bi-dataset"),
    path("reports/summary/", ReportSummaryAPIView.as_view(), name="reports-summary"),
    path("commercial-analytics/summary/", CommercialAnalyticsSummaryAPIView.as_view(), name="commercial-analytics-summary"),
    path("commercial-analytics/leads-dataset/", CommercialLeadDatasetAPIView.as_view(), name="commercial-leads-dataset"),
    path("reports/<slug:report_type>/", ReportDetailAPIView.as_view(), name="reports-detail"),
]
