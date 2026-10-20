"""ES: Este módulo especifica regresiones ejecutables para el dominio de calidad.

EN: This module specifies executable regressions for the quality domain.

Contexto existente / Existing context:
Regression coverage for e2e final stabilization v02326 in the quality domain.
"""

from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

from apps.leads.models import Lead


def _read(relative: str) -> str:
    return (Path(settings.BASE_DIR) / relative).read_text(encoding="utf-8")


def test_public_request_flow_uses_stable_success_contract():
    source = _read("tests/e2e/test_01_public.py")
    template = _read("templates/leads/public/request_success.html")

    assert 'get_by_role("button", name="Enviar solicitud")' in source
    assert "window.location.pathname.startsWith('/leads/request/success/')" in source
    assert 'Lead.objects.filter(email="publico.qa@example.com"' in source
    assert 'data-testid="lead-request-success"' in template
    assert 'id="lead-request-success-title"' in template



@pytest.mark.django_db
def test_public_success_page_renders_confirmation(client):
    lead = Lead.objects.create(
        full_name="Cliente Confirmación QA",
        email="confirmacion.qa@example.com",
        consent_data_processing=True,
    )
    session = client.session
    session["last_public_lead"] = str(lead.public_id)
    session.save()

    response = client.get(reverse("leads:public_success", kwargs={"public_id": lead.public_id}))

    assert response.status_code == 200
    assert b'data-testid="lead-request-success"' in response.content
    assert b'id="lead-request-success-title"' in response.content
    assert "Gracias por contactarnos" in response.content.decode("utf-8")
    assert lead.code.encode("utf-8") in response.content

def test_inventory_action_has_specific_accessible_name():
    source = _read("tests/e2e/test_05_inventory.py")
    template = _read("templates/inventory/internal/item_form.html")

    assert '>Guardar artículo</button>' in template
    assert 'get_by_role("button", name="Guardar artículo")' in source


def test_document_e2e_uses_allowed_pdf_and_verifies_persistence():
    source = _read("tests/e2e/test_07_documents.py")

    assert 'NamedTemporaryFile(suffix=".pdf"' in source
    assert r'b"%PDF-1.4\n"' in source
    assert 'PrivateDocument.objects.get(title="Documento E2E")' in source
    assert 'NamedTemporaryFile(suffix=".txt"' not in source


def test_mobile_internal_filters_are_contained():
    filters = _read("static/css/ui/components/filters.css")
    tables = _read("static/css/ui/components/tables.css")
    responsive = _read("static/css/ui/responsive/mobile.css")

    assert ".internal-filter-form, .inventory-filter-form" in filters
    assert ".main-content" in _read("static/css/ui/layouts/containers.css")
    assert ".responsive-table" in tables
    assert ".mobile-card-table td" in responsive
    assert ".mobile-card-table td::before" in responsive


def test_responsive_failure_reports_offending_elements():
    source = _read("tests/e2e/helpers/assertions.py")

    assert "const viewportWidth = document.documentElement.clientWidth" in source
    assert "item.right > viewportWidth + 2 || item.left < -2" in source
    assert "{offenders}" in source


def test_product_version_is_v02327():
    assert settings.VINOVA_PRODUCT_VERSION == "2.0.0"
    assert settings.SPECTACULAR_SETTINGS["VERSION"] == settings.VINOVA_PRODUCT_VERSION
