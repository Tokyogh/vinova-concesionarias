"""ES: Este módulo especifica regresiones ejecutables para el dominio de privacidad.

EN: This module specifies executable regressions for the privacy domain.

Contexto existente / Existing context:
Regresión del consentimiento de cookies y tecnologías opcionales.

Regression coverage for cookie consent and optional browser technologies.
"""

from __future__ import annotations

import pytest
from django.conf import settings
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.analytics.models import VehicleInteraction
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.privacy.cookies import encode_cookie_preferences, read_cookie_preferences
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel


pytestmark = pytest.mark.django_db


def _published_vehicle():
    company = Company.objects.create(legal_name="Empresa QA", commercial_name="Vinova", ruc="0999999999001")
    branch = Branch.objects.create(company=company, name="Sede QA", code="COOKIE-QA", city="Quito")
    brand = VehicleBrand.objects.create(name="Marca Cookie")
    model = VehicleModel.objects.create(brand=brand, name="Modelo Cookie")
    return Vehicle.objects.create(
        brand=brand,
        model=model,
        branch=branch,
        year=2026,
        price="25000.00",
        status=Vehicle.Status.AVAILABLE,
        public_slug="vehiculo-cookie-qa",
        published_at=timezone.now(),
    )


def test_undecided_user_sees_equal_choices_and_optional_categories_are_off(client):
    response = client.get(reverse("vehicles:catalog"))

    assert response.status_code == 200
    assert b"Aceptar opcionales" in response.content
    assert b"Rechazar opcionales" in response.content
    assert b'data-decided="0"' in response.content
    assert b'data-analytics="0"' in response.content
    assert settings.VINOVA_COOKIE_CONSENT_NAME not in response.cookies


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        ("accept_all", (True, True, True)),
        ("reject_optional", (False, False, False)),
        ("save", (True, False, True)),
    ],
)
def test_preference_actions_set_signed_http_only_cookie(client, rf, action, expected):
    payload = {"action": action, "next": "/vehiculos/"}
    if action == "save":
        payload.update({"preferences": "on", "external_media": "on"})

    response = client.post(reverse("privacy_public:cookie_update"), payload)

    assert response.status_code == 302
    assert response.headers["Location"] == "/vehiculos/"
    morsel = response.cookies[settings.VINOVA_COOKIE_CONSENT_NAME]
    assert morsel["httponly"]
    assert morsel["samesite"] == "Lax"
    assert morsel["path"] == "/"
    request = rf.get("/", HTTP_COOKIE=f"{settings.VINOVA_COOKIE_CONSENT_NAME}={morsel.value}")
    preferences = read_cookie_preferences(request)
    assert preferences.decided is True
    assert (preferences.preferences, preferences.analytics, preferences.external_media) == expected
    assert preferences.version == settings.VINOVA_COOKIE_NOTICE_VERSION
    assert preferences.updated_at


def test_tampered_or_outdated_cookie_requires_a_new_decision(client):
    client.cookies[settings.VINOVA_COOKIE_CONSENT_NAME] = "tampered"
    response = client.get(reverse("privacy_public:cookie_settings"))

    assert response.status_code == 200
    assert response.context["current_preferences"].decided is False

    with override_settings(VINOVA_COOKIE_NOTICE_VERSION="next-version"):
        client.cookies[settings.VINOVA_COOKIE_CONSENT_NAME] = encode_cookie_preferences(
            preferences=True,
            analytics=True,
            external_media=True,
        )
    with override_settings(VINOVA_COOKIE_NOTICE_VERSION="current-version"):
        response = client.get(reverse("vehicles:catalog"))
    assert b'data-decided="0"' in response.content


def test_cookie_update_rejects_external_redirect(client):
    response = client.post(
        reverse("privacy_public:cookie_update"),
        {"action": "reject_optional", "next": "https://attacker.example/phish"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("privacy_public:cookie_settings")


def test_vehicle_analytics_requires_explicit_analytics_consent(client):
    vehicle = _published_vehicle()

    response = client.get(reverse("vehicles:detail", kwargs={"slug": vehicle.public_slug}))
    assert response.status_code == 200
    assert VehicleInteraction.objects.count() == 0
    assert settings.SESSION_COOKIE_NAME not in client.cookies

    client.cookies[settings.VINOVA_COOKIE_CONSENT_NAME] = encode_cookie_preferences(
        preferences=False,
        analytics=True,
        external_media=False,
    )
    response = client.get(reverse("vehicles:detail", kwargs={"slug": vehicle.public_slug}))
    assert response.status_code == 200
    assert VehicleInteraction.objects.filter(
        event_type=VehicleInteraction.EventType.DETAIL_VIEW,
        vehicle=vehicle,
    ).count() == 1


@override_settings(MAPTILER_PUBLIC_KEY="public-browser-key")
def test_external_map_assets_and_key_require_external_media_consent(client):
    response = client.get(reverse("institutions:list"))

    assert b"unpkg.com/maplibre-gl" not in response.content
    assert b"public-browser-key" not in response.content
    assert b"Configurar privacidad" in response.content

    client.cookies[settings.VINOVA_COOKIE_CONSENT_NAME] = encode_cookie_preferences(
        preferences=False,
        analytics=False,
        external_media=True,
    )
    response = client.get(reverse("institutions:list"))
    assert b"unpkg.com/maplibre-gl" in response.content
    assert b'data-maptiler-key="public-browser-key"' in response.content


def test_settings_page_allows_revocation_and_does_not_repeat_banner(client):
    client.cookies[settings.VINOVA_COOKIE_CONSENT_NAME] = encode_cookie_preferences(
        preferences=True,
        analytics=True,
        external_media=True,
    )
    page = client.get(reverse("privacy_public:cookie_settings"))
    assert page.status_code == 200
    assert b"Guardar preferencias" in page.content
    assert b'class="cookie-consent"' not in page.content

    client.post(reverse("privacy_public:cookie_update"), {"action": "reject_optional"})
    response = client.get(reverse("vehicles:catalog"))
    assert b'data-decided="1"' in response.content
    assert b'data-preferences="0"' in response.content
    assert b'data-analytics="0"' in response.content
    assert b'data-external-media="0"' in response.content
    assert b'class="cookie-consent"' not in response.content
