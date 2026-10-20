"""ES: Este módulo declara el enrutamiento URL para el dominio de auditoría.

EN: This module declares URL routing for the audit domain.

Contexto existente / Existing context:
URL routing for the audit domain.
"""

from django.urls import path

from apps.audit.views import (
    AuditExportView,
    AuditIntegrityView,
    AuditLogDetailView,
    AuditLogListView,
    SecurityAlertDetailView,
    SecurityAlertListView,
    SecurityAlertUpdateView,
)

app_name = "audit_internal"

urlpatterns = [
    path("", AuditLogListView.as_view(), name="list"),
    path("export/", AuditExportView.as_view(), name="export"),
    path("integrity/", AuditIntegrityView.as_view(), name="integrity"),
    path("alerts/", SecurityAlertListView.as_view(), name="alerts"),
    path("alerts/<uuid:alert_id>/", SecurityAlertDetailView.as_view(), name="alert_detail"),
    path("alerts/<uuid:alert_id>/update/", SecurityAlertUpdateView.as_view(), name="alert_update"),
    path("<uuid:event_id>/", AuditLogDetailView.as_view(), name="detail"),
]
