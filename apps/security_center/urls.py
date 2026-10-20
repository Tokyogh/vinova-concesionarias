"""ES: Este módulo declara el enrutamiento URL para el dominio de seguridad.

EN: This module declares URL routing for the security center domain.

Contexto existente / Existing context:
URL routing for the security center domain.
"""

from django.urls import path

from apps.security_center.views import AdminResetTwoFactorView, ApproveStaffAccessView, BackupCodesView, CancelStaffAccessView, MySessionsView, RejectStaffAccessView, RevokeSessionView, RevokeStaffAccessView, SecurePasswordChangeView, SecurityDashboardView, SecurityPolicyUpdateView, StaffAccessPendingView, StaffAccessRequestListView, TwoFactorChallengeView, TwoFactorDisableView, TwoFactorSetupView

app_name = "security_center"
urlpatterns = [
    path("dashboard/security/", SecurityDashboardView.as_view(), name="dashboard"),
    path("dashboard/security/policy/", SecurityPolicyUpdateView.as_view(), name="policy"),
    path("security/2fa/setup/", TwoFactorSetupView.as_view(), name="two_factor_setup"),
    path("security/2fa/challenge/", TwoFactorChallengeView.as_view(), name="two_factor_challenge"),
    path("security/2fa/backup-codes/", BackupCodesView.as_view(), name="backup_codes"),
    path("security/2fa/disable/", TwoFactorDisableView.as_view(), name="two_factor_disable"),
    path("security/password/change/", SecurePasswordChangeView.as_view(), name="password_change"),
    path("security/sessions/", MySessionsView.as_view(), name="my_sessions"),
    path("security/sessions/<int:pk>/revoke/", RevokeSessionView.as_view(), name="revoke_session"),
    path("security/staff-access/", StaffAccessPendingView.as_view(), name="staff_access_pending"),
    path("security/staff-access/cancel/", CancelStaffAccessView.as_view(), name="staff_access_cancel"),
    path("dashboard/security/staff-access/", StaffAccessRequestListView.as_view(), name="staff_access_requests"),
    path("dashboard/security/staff-access/<int:pk>/approve/", ApproveStaffAccessView.as_view(), name="staff_access_approve"),
    path("dashboard/security/staff-access/<int:pk>/reject/", RejectStaffAccessView.as_view(), name="staff_access_reject"),
    path("dashboard/security/staff-access/<int:pk>/revoke/", RevokeStaffAccessView.as_view(), name="staff_access_revoke"),
    path("dashboard/security/users/<int:pk>/reset-2fa/", AdminResetTwoFactorView.as_view(), name="admin_reset_2fa"),
]
