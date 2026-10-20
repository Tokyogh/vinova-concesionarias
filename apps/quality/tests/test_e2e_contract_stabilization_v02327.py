"""ES: Este módulo especifica regresiones ejecutables para el dominio de calidad.

EN: This module specifies executable regressions for the quality domain.

Contexto existente / Existing context:
Regression coverage for e2e contract stabilization v02327 in the quality domain.
"""

from pathlib import Path

import pytest
from django.conf import settings

from apps.customers.forms import CustomerSearchForm


def _read(relative: str) -> str:
    return (Path(settings.BASE_DIR) / relative).read_text(encoding="utf-8")


def test_inventory_e2e_uses_detail_inline_post_contract():
    source = _read("tests/e2e/test_05_inventory.py")
    view_source = _read("apps/inventory/views.py")

    assert 'movement_form = self.page.locator("form.inventory-inline-form")' in source
    assert 'name="Guardar movimiento"' in source
    assert '/stock/new/")' not in source
    assert "class InternalItemStockMovementCreateView" in view_source
    assert "def post(self, request, pk):" in view_source
    assert "def get(self, request, pk):" not in view_source


def test_document_heading_selector_is_unambiguous():
    source = _read("tests/e2e/test_07_documents.py")

    assert 'get_by_role("heading", name="Documento E2E", level=1)' in source


@pytest.mark.django_db
def test_customer_search_filters_have_accessible_names():
    form = CustomerSearchForm()

    assert set(form.fields) == {
        "q", "identification", "first_name", "last_name", "email", "phone",
        "plate", "vin", "status", "customer_type", "branch", "sort",
    }
    for field in form.fields.values():
        assert field.widget.attrs.get("aria-label") == field.label


def test_product_version_is_v02327():
    assert settings.VINOVA_PRODUCT_VERSION == "2.0.0"
    assert settings.SPECTACULAR_SETTINGS["VERSION"] == settings.VINOVA_PRODUCT_VERSION
