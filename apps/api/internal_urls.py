"""ES: Este módulo implementa el componente internal urls para el dominio de API e integraciones.

EN: This module implements the internal urls component for the api domain.

Contexto existente / Existing context:
Internal urls support for the api domain.
"""

from django.urls import path

from apps.api.internal_views import APIClientCreateView, APIClientRotateView, IntegrationDashboardView, WebhookCreateView, WebhookTestView

app_name = "api_internal"

urlpatterns = [
    path("", IntegrationDashboardView.as_view(), name="dashboard"),
    path("clients/new/", APIClientCreateView.as_view(), name="client_create"),
    path("clients/<uuid:public_id>/rotate/", APIClientRotateView.as_view(), name="client_rotate"),
    path("webhooks/new/", WebhookCreateView.as_view(), name="webhook_create"),
    path("webhooks/<uuid:public_id>/test/", WebhookTestView.as_view(), name="webhook_test"),
]
