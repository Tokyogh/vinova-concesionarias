"""ES: Este módulo implementa el componente public urls para el dominio de privacidad.

EN: This module implements the public urls component for the privacy domain.

Contexto existente / Existing context:
Public urls support for the privacy domain.
"""

from django.urls import path
from django.views.generic import TemplateView

from apps.privacy.views import CookiePreferencesUpdateView, CookiePreferencesView, PublicDataSubjectRequestView, PublicDataSubjectThanksView

app_name = "privacy_public"
urlpatterns = [
    path("cookies/", CookiePreferencesView.as_view(), name="cookie_settings"),
    path("cookies/update/", CookiePreferencesUpdateView.as_view(), name="cookie_update"),
    path(
        "policy/",
        TemplateView.as_view(template_name="privacy/public/privacy_policy.html"),
        name="privacy_policy",
    ),
    path(
        "cookie-policy/",
        TemplateView.as_view(template_name="privacy/public/cookie_policy.html"),
        name="cookie_policy",
    ),
    path(
        "terms/",
        TemplateView.as_view(template_name="privacy/public/terms.html"),
        name="terms",
    ),
    path(
        "legal-notice/",
        TemplateView.as_view(template_name="privacy/public/legal_notice.html"),
        name="legal_notice",
    ),
    path("request/", PublicDataSubjectRequestView.as_view(), name="request"),
    path("request/thanks/", PublicDataSubjectThanksView.as_view(), name="thanks"),
]
