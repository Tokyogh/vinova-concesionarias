"""ES: Este módulo declara el enrutamiento URL para el dominio de CRM y leads.

EN: This module declares URL routing for the leads domain.

Contexto existente / Existing context:
URL routing for the leads domain.
"""

from django.urls import path

from apps.leads.views import PublicLeadRequestView, PublicLeadSuccessView

app_name = "leads"

urlpatterns = [
    path("request/", PublicLeadRequestView.as_view(), name="public_request"),
    path("request/vehicle/<int:vehicle_id>/", PublicLeadRequestView.as_view(), name="public_vehicle_request"),
    path("request/success/<uuid:public_id>/", PublicLeadSuccessView.as_view(), name="public_success"),
]
