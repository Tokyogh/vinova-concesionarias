"""ES: Este módulo especifica regresiones ejecutables para el dominio de infraestructura compartida.

EN: This module specifies executable regressions for the common domain.

Contexto existente / Existing context:
Regression coverage for universal search in the common domain.
"""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.common.universal_search import universal_search_for_user
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel


def _search_context(django_user_model):
    company = Company.objects.create(
        legal_name="Búsqueda Segura S.A.",
        commercial_name="Búsqueda Segura",
        ruc="1799999999028",
    )
    own_branch = Branch.objects.create(company=company, name="Matriz", code="SEARCH-A", city="Quito")
    other_branch = Branch.objects.create(company=company, name="Sur", code="SEARCH-B", city="Cuenca")
    permission = PermissionCode.objects.create(module="vehicles", code="vehicles.view", name="Ver vehículos")
    role = Role.objects.create(code="search_vehicle_viewer", name="Buscador vehículos")
    role.permissions.add(permission)
    user = django_user_model.objects.create_user(
        username="search-scoped", email="search-scoped@example.com", password="StrongPass-2026!"
    )
    UserRole.objects.create(user=user, role=role, branch=own_branch)
    brand = VehicleBrand.objects.create(name="Needle Motors")
    model = VehicleModel.objects.create(brand=brand, name="Scope")
    own_vehicle = Vehicle.objects.create(
        brand=brand,
        model=model,
        branch=own_branch,
        year=2026,
        version="Needle visible",
        vin="SEARCHNEEDLE0001",
        price=Decimal("25000.00"),
        public_slug="search-needle-visible",
    )
    other_vehicle = Vehicle.objects.create(
        brand=brand,
        model=model,
        branch=other_branch,
        year=2026,
        version="Needle restringido",
        vin="SEARCHNEEDLE0002",
        price=Decimal("26000.00"),
        public_slug="search-needle-restricted",
    )
    customer = Customer.objects.create(
        first_name="Needle",
        last_name="Cliente",
        identification_number="0911111111",
        email="needle@example.com",
        assigned_branch=own_branch,
    )
    return user, own_vehicle, other_vehicle, customer


@pytest.mark.django_db
def test_universal_search_authorizes_source_and_filters_branch_scope(django_user_model):
    user, own_vehicle, other_vehicle, customer = _search_context(django_user_model)

    payload = universal_search_for_user(user, "Needle")
    keys = {result["key"] for result in payload["results"]}

    assert f"entity:vehicle:{own_vehicle.pk}" in keys
    assert f"entity:vehicle:{other_vehicle.pk}" not in keys
    assert f"entity:customer:{customer.pk}" not in keys
    assert all(result["area"] == "Vehículos" for result in payload["results"])


@pytest.mark.django_db
def test_universal_search_uses_bounded_queries_for_one_authorized_source(
    django_assert_num_queries, django_user_model
):
    user, own_vehicle, _, _ = _search_context(django_user_model)

    with django_assert_num_queries(4):
        payload = universal_search_for_user(user, own_vehicle.vin)

    assert payload["results"][0]["url"] == reverse("vehicles_internal:detail", args=[own_vehicle.pk])


@pytest.mark.django_db
def test_universal_search_endpoint_requires_internal_access(client, django_user_model):
    common = django_user_model.objects.create_user(
        username="search-common", email="search-common@example.com", password="StrongPass-2026!"
    )
    client.force_login(common)

    assert client.get(reverse("dashboard:universal_search"), {"q": "Needle"}).status_code == 403


@pytest.mark.django_db
def test_universal_search_endpoint_returns_only_scoped_records(client, django_user_model):
    user, own_vehicle, other_vehicle, _ = _search_context(django_user_model)
    client.force_login(user)

    response = client.get(reverse("dashboard:universal_search"), {"q": "Needle"})
    keys = {result["key"] for result in response.json()["results"]}

    assert response.status_code == 200
    assert f"entity:vehicle:{own_vehicle.pk}" in keys
    assert f"entity:vehicle:{other_vehicle.pk}" not in keys


@pytest.mark.django_db
def test_universal_search_ignores_short_queries(django_user_model):
    user, *_ = _search_context(django_user_model)

    assert universal_search_for_user(user, "N") == {"query": "N", "count": 0, "results": []}
