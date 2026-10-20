"""ES: Este módulo declara el enrutamiento URL para el dominio de privacidad.

EN: This module declares URL routing for the privacy domain.

Contexto existente / Existing context:
URL routing for the privacy domain.
"""

from django.urls import path

from apps.privacy.views import (
    ConsentListView, DataExportDownloadView, DataSubjectAnonymizeView, DataSubjectExportView,
    DataSubjectRequestCreateView, DataSubjectRequestDetailView, DataSubjectRequestListView,
    DataSubjectRequestStatusView, DataSubjectRequestUpdateView, PrivacyDashboardView,
    RetentionPolicyCreateView, RetentionPolicyListView, RetentionPolicyUpdateView,
)

app_name = "privacy"
urlpatterns = [
    path("", PrivacyDashboardView.as_view(), name="dashboard"),
    path("requests/", DataSubjectRequestListView.as_view(), name="request_list"),
    path("requests/new/", DataSubjectRequestCreateView.as_view(), name="request_create"),
    path("requests/<uuid:public_id>/", DataSubjectRequestDetailView.as_view(), name="request_detail"),
    path("requests/<uuid:public_id>/edit/", DataSubjectRequestUpdateView.as_view(), name="request_update"),
    path("requests/<uuid:public_id>/status/", DataSubjectRequestStatusView.as_view(), name="request_status"),
    path("requests/<uuid:public_id>/export/", DataSubjectExportView.as_view(), name="request_export"),
    path("requests/<uuid:public_id>/anonymize/", DataSubjectAnonymizeView.as_view(), name="request_anonymize"),
    path("exports/<uuid:public_id>/download/", DataExportDownloadView.as_view(), name="export_download"),
    path("consents/", ConsentListView.as_view(), name="consent_list"),
    path("retention/", RetentionPolicyListView.as_view(), name="retention_list"),
    path("retention/new/", RetentionPolicyCreateView.as_view(), name="retention_create"),
    path("retention/<int:pk>/edit/", RetentionPolicyUpdateView.as_view(), name="retention_update"),
]
