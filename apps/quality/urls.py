"""ES: Este módulo declara el enrutamiento URL para el dominio de calidad.

EN: This module declares URL routing for the quality domain.

Contexto existente / Existing context:
URL routing for the quality domain.
"""

from django.urls import path

from apps.quality.views import (
    QualityReportDownloadView,
    QualityRunCreateView,
    QualityRunDetailView,
    QualityRunListView,
)

app_name = "quality"

urlpatterns = [
    path("", QualityRunListView.as_view(), name="run_list"),
    path("run/", QualityRunCreateView.as_view(), name="run_create"),
    path("runs/<uuid:public_id>/", QualityRunDetailView.as_view(), name="run_detail"),
    path(
        "runs/<uuid:public_id>/reports/<str:report_format>/",
        QualityReportDownloadView.as_view(),
        name="report_download",
    ),
]
