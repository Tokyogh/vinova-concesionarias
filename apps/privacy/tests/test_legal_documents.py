"""ES: Este módulo especifica regresiones ejecutables para el dominio de privacidad.

EN: This module specifies executable regressions for the privacy domain.

Contexto existente / Existing context:
Regresión de borradores legales, navegación y campos empresariales.

Regression coverage for legal drafts, navigation, and company fields.
"""

import pytest
from django.urls import reverse

from apps.companies.models import Company
from apps.enterprise.models import CompanyPublicSettings


pytestmark = pytest.mark.django_db

LEGAL_ROUTES = (
    "privacy_public:privacy_policy",
    "privacy_public:cookie_policy",
    "privacy_public:terms",
    "privacy_public:legal_notice",
)


@pytest.mark.parametrize("route_name", LEGAL_ROUTES)
def test_legal_documents_are_public_and_clearly_marked_as_drafts(client, route_name):
    response = client.get(reverse(route_name))

    assert response.status_code == 200
    assert "Borrador técnico pendiente de revisión profesional" in response.content.decode()
    assert "No constituye asesoría legal" in response.content.decode()
    assert b"privacy/cookies/" in response.content


def test_privacy_policy_uses_configured_identity_without_inventing_missing_fields(client):
    company = Company.objects.create(
        legal_name="Empresa Configurada S.A.",
        commercial_name="Empresa Configurada",
        ruc="0999999999001",
        email="privacidad@example.com",
        address="",
    )
    CompanyPublicSettings.objects.create(
        company=company,
        privacy_policy="Texto interno sujeto a revisión.",
        data_processing_summary="Resumen configurado.",
    )

    body = client.get(reverse("privacy_public:privacy_policy")).content.decode()

    assert "Empresa Configurada S.A." in body
    assert "0999999999001" in body
    assert "privacidad@example.com" in body
    assert "PENDIENTE DE COMPLETAR" in body
    assert "Texto interno sujeto a revisión." in body
    assert "Resumen configurado." in body


def test_public_footer_links_every_legal_document(client):
    body = client.get("/").content.decode()

    for route_name in LEGAL_ROUTES:
        assert reverse(route_name) in body
