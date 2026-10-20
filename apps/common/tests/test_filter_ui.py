"""ES: Este módulo especifica regresiones ejecutables para el dominio de infraestructura compartida.

EN: This module specifies executable regressions for the common domain.

Contexto existente / Existing context:
Regression coverage for filter ui in the common domain.
"""

from types import SimpleNamespace

import pytest
from django.test import RequestFactory

from apps.common.templatetags.filter_ui import filter_querystring, vinova_filter_panel
from apps.customers.forms import CustomerSearchForm
from apps.documents.forms import DocumentSearchForm
from apps.inventory.forms import InventoryItemSearchForm
from apps.invoices.forms import InvoiceSearchForm
from apps.leads.forms import LeadSearchForm
from apps.sales.forms import SaleSearchForm
from apps.vehicles.forms import VehicleSearchForm


@pytest.mark.django_db
def test_filter_panel_builds_removable_chips_and_preserves_other_query_values():
    request = RequestFactory().get("/dashboard/customers/", {"q": "Ana", "status": "active", "page": "3"})
    request.user = SimpleNamespace(pk=17)
    form = CustomerSearchForm(request.GET)
    assert form.is_valid()

    context = vinova_filter_panel(
        {"request": request}, form, "/dashboard/customers/", "customers",
        common="q,status,sort", advanced="customer_type,branch",
    )

    assert [chip["label"] for chip in context["chips"]] == ["Buscar", "Estado"]
    assert context["chips"][0]["href"] == "/dashboard/customers/?status=active"
    assert context["chips"][1]["href"] == "/dashboard/customers/?q=Ana"
    assert filter_querystring({"request": request}, page=2) == "?q=Ana&status=active&page=2"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "form_class",
    [
        VehicleSearchForm, CustomerSearchForm, SaleSearchForm, InventoryItemSearchForm,
        InvoiceSearchForm, LeadSearchForm, DocumentSearchForm,
    ],
)
def test_filter_forms_reject_non_allowlisted_ordering(form_class):
    form = form_class({"sort": "-created_at;DROP TABLE"})
    assert not form.is_valid()
    assert "sort" in form.errors
