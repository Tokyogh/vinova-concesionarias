"""ES: Este módulo declara el enrutamiento URL para el dominio de analítica.

EN: This module declares URL routing for the analytics domain.

Contexto existente / Existing context:
URL routing for the analytics domain.
"""

from django.urls import path

from apps.analytics.views import CommercialAnalyticsExportView, CommercialAnalyticsView

app_name = "analytics_internal"
urlpatterns = [
    path("", CommercialAnalyticsView.as_view(), name="home"),
    path("export/", CommercialAnalyticsExportView.as_view(), name="export"),
]
