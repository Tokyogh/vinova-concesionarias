"""ES: Este módulo implementa el componente context processors para el dominio de privacidad.

EN: This module implements the context processors component for the privacy domain.

Contexto existente / Existing context:
Contexto de consentimiento para plantillas públicas, Staff y portal.

Consent context for public, Staff, and portal templates.
"""

from django.conf import settings

from apps.privacy.cookies import read_cookie_preferences


def cookie_preferences_context(request):
    preferences = read_cookie_preferences(request)
    return {
        "vinova_cookie_preferences": preferences,
        "vinova_cookie_consent_required": not preferences.decided,
        "vinova_privacy_notice_version": settings.VINOVA_PRIVACY_NOTICE_VERSION,
        "vinova_terms_version": settings.VINOVA_TERMS_VERSION,
    }
