"""ES: Este módulo declara el enrutamiento URL para el dominio de configuración empresarial.

EN: This module declares URL routing for the enterprise domain.

Contexto existente / Existing context:
URL routing for the enterprise domain.
"""

from django.urls import path

from apps.enterprise.views import (
    ApprovalPolicyListView,
    ApprovalPolicyUpdateView,
    CompanyProfileUpdateView,
    EnterpriseHomeView,
    LegalSettingsUpdateView,
    PublicContactUpdateView,
    PublicSiteUpdateView,
)

app_name = "enterprise"

urlpatterns = [
    path("", EnterpriseHomeView.as_view(), name="home"),
    path("profile/", CompanyProfileUpdateView.as_view(), name="profile"),
    path("branding/", CompanyProfileUpdateView.as_view(), name="branding"),
    path("public-site/", PublicSiteUpdateView.as_view(), name="public_site"),
    path("contact/", PublicContactUpdateView.as_view(), name="contact"),
    path("legal/", LegalSettingsUpdateView.as_view(), name="legal"),
    path("approval-policies/", ApprovalPolicyListView.as_view(), name="approval_policies"),
    path("approval-policies/<int:pk>/", ApprovalPolicyUpdateView.as_view(), name="approval_policy_update"),
]
