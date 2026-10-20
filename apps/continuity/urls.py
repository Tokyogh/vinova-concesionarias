"""ES: Este módulo declara el enrutamiento URL para el dominio de continuidad.

EN: This module declares URL routing for the continuity domain.

Contexto existente / Existing context:
URL routing for the continuity domain.
"""

from django.urls import path

from apps.continuity.views import (
    BackupCreateView, BackupDetailView, BackupDownloadView, BackupListView, BackupPolicyUpdateView,
    BackupVerifyView, ContinuityDashboardView, RestoreDrillCompleteView, RestoreDrillCreateView, RestoreDrillDetailView,
    UpdateCenterView,
)

app_name = "continuity"
urlpatterns = [
    path("", ContinuityDashboardView.as_view(), name="dashboard"),
    path("updates/", UpdateCenterView.as_view(), name="update_center"),
    path("backups/", BackupListView.as_view(), name="backup_list"),
    path("backups/create/", BackupCreateView.as_view(), name="backup_create"),
    path("backups/<uuid:public_id>/", BackupDetailView.as_view(), name="backup_detail"),
    path("backups/<uuid:public_id>/verify/", BackupVerifyView.as_view(), name="backup_verify"),
    path("backups/<uuid:public_id>/download/", BackupDownloadView.as_view(), name="backup_download"),
    path("policy/", BackupPolicyUpdateView.as_view(), name="policy"),
    path("restore-drills/create/", RestoreDrillCreateView.as_view(), name="restore_create"),
    path("restore-drills/<uuid:public_id>/", RestoreDrillDetailView.as_view(), name="restore_detail"),
    path("restore-drills/<uuid:public_id>/complete/", RestoreDrillCompleteView.as_view(), name="restore_complete"),
]
