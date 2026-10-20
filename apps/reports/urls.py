"""ES: Este módulo declara el enrutamiento URL para el dominio de reportes.

EN: This module declares URL routing for the reports domain.

Contexto existente / Existing context:
URL routing for the reports domain.
"""

from django.urls import path

from apps.reports.views import DynamicReportDetailView, ReportExportView, ReportPrintView, ReportsHomeView

app_name = "reports_internal"

urlpatterns = [
    path("", ReportsHomeView.as_view(), name="home"),
    path("<slug:report_type>/", DynamicReportDetailView.as_view(), name="detail"),
    path("<slug:report_type>/export/<slug:export_format>/", ReportExportView.as_view(), name="export"),
    path("<slug:report_type>/print/", ReportPrintView.as_view(), name="print"),
]
