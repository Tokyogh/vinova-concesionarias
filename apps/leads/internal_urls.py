"""ES: Este módulo implementa el componente internal urls para el dominio de CRM y leads.

EN: This module implements the internal urls component for the leads domain.

Contexto existente / Existing context:
Internal urls support for the leads domain.
"""

from django.urls import path

from apps.leads.views import (
    InternalLeadActivityView, InternalLeadAssignmentView, InternalLeadConvertCustomerView, InternalLeadCreateQuoteView,
    InternalLeadCreateView, InternalLeadDetailView, InternalLeadExportView, InternalLeadListView, InternalLeadPipelineView,
    InternalLeadStatusView, InternalLeadTestDriveView, InternalLeadUpdateView,
)

app_name = "leads_internal"

urlpatterns = [
    path("", InternalLeadListView.as_view(), name="list"),
    path("pipeline/", InternalLeadPipelineView.as_view(), name="pipeline"),
    path("new/", InternalLeadCreateView.as_view(), name="create"),
    path("export/", InternalLeadExportView.as_view(), name="export"),
    path("<int:pk>/", InternalLeadDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", InternalLeadUpdateView.as_view(), name="update"),
    path("<int:pk>/status/", InternalLeadStatusView.as_view(), name="status"),
    path("<int:pk>/activity/", InternalLeadActivityView.as_view(), name="activity"),
    path("<int:pk>/assign/", InternalLeadAssignmentView.as_view(), name="assign"),
    path("<int:pk>/test-drive/", InternalLeadTestDriveView.as_view(), name="test_drive"),
    path("<int:pk>/convert-customer/", InternalLeadConvertCustomerView.as_view(), name="convert_customer"),
    path("<int:pk>/create-quote/", InternalLeadCreateQuoteView.as_view(), name="create_quote"),
]
