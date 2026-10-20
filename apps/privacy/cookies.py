"""ES: Este módulo implementa el componente cookies para el dominio de privacidad.

EN: This module implements the cookies component for the privacy domain.

Contexto existente / Existing context:
Preferencias firmadas y mínimas para tecnologías opcionales del navegador.

Signed, minimal preferences for optional browser technologies.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from django.conf import settings
from django.core import signing
from django.utils import timezone

COOKIE_SALT = "vinova.cookie-preferences.v1"


@dataclass(frozen=True)
class CookiePreferences:
    version: str
    updated_at: str
    preferences: bool = False
    analytics: bool = False
    external_media: bool = False
    decided: bool = False

    def allows(self, category: str) -> bool:
        return bool(self.decided and getattr(self, category, False))


def undecided_cookie_preferences() -> CookiePreferences:
    return CookiePreferences(
        version=settings.VINOVA_COOKIE_NOTICE_VERSION,
        updated_at="",
    )


def encode_cookie_preferences(*, preferences: bool, analytics: bool, external_media: bool) -> str:
    payload = CookiePreferences(
        version=settings.VINOVA_COOKIE_NOTICE_VERSION,
        updated_at=timezone.now().isoformat(),
        preferences=bool(preferences),
        analytics=bool(analytics),
        external_media=bool(external_media),
        decided=True,
    )
    return signing.dumps(asdict(payload), salt=COOKIE_SALT, compress=True)


def read_cookie_preferences(request) -> CookiePreferences:
    encoded = request.COOKIES.get(settings.VINOVA_COOKIE_CONSENT_NAME, "")
    if not encoded:
        return undecided_cookie_preferences()
    try:
        payload = signing.loads(
            encoded,
            salt=COOKIE_SALT,
            max_age=settings.VINOVA_COOKIE_CONSENT_AGE,
        )
    except signing.BadSignature:
        return undecided_cookie_preferences()
    if not isinstance(payload, dict) or payload.get("version") != settings.VINOVA_COOKIE_NOTICE_VERSION:
        return undecided_cookie_preferences()
    return CookiePreferences(
        version=str(payload["version"]),
        updated_at=str(payload.get("updated_at", ""))[:64],
        preferences=payload.get("preferences") is True,
        analytics=payload.get("analytics") is True,
        external_media=payload.get("external_media") is True,
        decided=payload.get("decided") is True,
    )


def cookie_category_allowed(request, category: str) -> bool:
    return read_cookie_preferences(request).allows(category)
