"""ES: Este módulo especifica regresiones ejecutables para el dominio de calidad.

EN: This module specifies executable regressions for the quality domain.

Contexto existente / Existing context:
Regression coverage for e2e expectation stabilization v02325 in the quality domain.
"""

from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel


def _e2e_source() -> str:
    root = Path(settings.BASE_DIR)
    paths = (
        "tests/e2e/helpers/auth.py",
        "tests/e2e/helpers/factories.py",
        "tests/e2e/test_01_public.py",
    )
    return "\n".join((root / path).read_text(encoding="utf-8") for path in paths)


def test_login_helper_validates_authenticated_internal_contract():
    source = _e2e_source()

    assert "window.location.pathname.startsWith('/dashboard/')" in source
    assert 'page.locator("#main-content").is_visible()' in source
    assert "nav[aria-label='Navegación interna']" in source
    assert 'page.get_by_role("button", name="Salir").is_visible()' in source
    assert 'assert "/accounts/profile/" in self.page.url' not in source


def test_public_catalog_fixture_meets_real_publication_rule():
    source = _e2e_source()
    fixture_start = source.index("test_case.vehicle = Vehicle.objects.create(")
    fixture_end = source.index("test_case.customer = Customer.objects.create(", fixture_start)
    vehicle_fixture = source[fixture_start:fixture_end]

    assert "status=Vehicle.Status.AVAILABLE" in vehicle_fixture
    assert "published_at=timezone.now()" in vehicle_fixture
    assert 'public_slug="foton-tunland-qa"' in vehicle_fixture
    assert 'price=Decimal("35000.00")' in vehicle_fixture


@pytest.mark.django_db
def test_internal_user_login_redirects_to_real_dashboard(client):
    company = Company.objects.create(
        legal_name="Vinova Login QA S.A.",
        commercial_name="Vinova Login QA",
        ruc="1799999999002",
    )
    branch = Branch.objects.create(
        company=company,
        name="Matriz Login QA",
        code="QA-LOGIN",
        branch_type=Branch.BranchType.DEALERSHIP,
        city="Quito",
    )
    password = "Vinova-QA-Login-2026!"
    user = User.objects.create_superuser(
        username="qa-login-admin",
        email="qa-login-admin@example.com",
        password=password,
        branch=branch,
    )

    response = client.post(reverse("accounts:login"), {"username": user.username, "password": password})

    assert response.status_code == 302
    assert response.url == reverse("dashboard:staff_home")
    dashboard = client.get(response.url)
    assert dashboard.status_code == 200
    assert b'id="main-content"' in dashboard.content
    assert b'Navegaci\xc3\xb3n interna' in dashboard.content
    assert b'>Salir<' in dashboard.content


@pytest.mark.django_db
def test_published_e2e_vehicle_is_visible_in_filtered_public_catalog(client):
    company = Company.objects.create(
        legal_name="Vinova Catalog QA S.A.",
        commercial_name="Vinova Catalog QA",
        ruc="1799999999003",
    )
    branch = Branch.objects.create(
        company=company,
        name="Matriz Catalog QA",
        code="QA-CATALOG",
        branch_type=Branch.BranchType.DEALERSHIP,
        city="Quito",
    )
    brand = VehicleBrand.objects.create(name="Foton E2E QA")
    model = VehicleModel.objects.create(brand=brand, name="Tunland QA")
    Vehicle.objects.create(
        brand=brand,
        model=model,
        branch=branch,
        year=2026,
        version="G7",
        vin="VINQA000000000002",
        public_slug="foton-tunland-qa-regression",
        status=Vehicle.Status.AVAILABLE,
        published_at=timezone.now(),
        price=Decimal("35000.00"),
        short_description="Vehículo QA disponible",
    )

    response = client.get(reverse("vehicles:catalog"), {"q": "Tunland"})

    assert response.status_code == 200
    assert b"Tunland QA" in response.content


def test_product_version_is_v02325():
    assert settings.VINOVA_PRODUCT_VERSION == "2.0.0"
    assert settings.SPECTACULAR_SETTINGS["VERSION"] == settings.VINOVA_PRODUCT_VERSION
