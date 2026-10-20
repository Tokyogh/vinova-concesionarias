"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for factories in the e2e helpers domain.
"""

from __future__ import annotations

from decimal import Decimal

from django.utils import timezone

from apps.accounts.models import User
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.inventory.models import InventoryCategory, InventoryItem
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel


def create_core_data(test_case) -> None:
    """Create deterministic data used by one isolated E2E scenario."""

    test_case.company = Company.objects.create(
        legal_name="Vinova QA Motors S.A.",
        commercial_name="Vinova QA",
        ruc="1799999999001",
    )
    test_case.branch = Branch.objects.create(
        company=test_case.company,
        name="Matriz QA",
        code="QA-MTR",
        branch_type=Branch.BranchType.DEALERSHIP,
        city="Quito",
    )
    test_case.admin = User.objects.create_superuser(
        username="qa-admin",
        email="qa-admin@example.com",
        password=test_case.password,
        branch=test_case.branch,
    )
    test_case.brand = VehicleBrand.objects.create(name="Foton QA")
    test_case.vehicle_model = VehicleModel.objects.create(brand=test_case.brand, name="Tunland QA")
    test_case.vehicle = Vehicle.objects.create(
        brand=test_case.brand,
        model=test_case.vehicle_model,
        branch=test_case.branch,
        year=2026,
        version="G7",
        vin="VINQA000000000001",
        public_slug="foton-tunland-qa",
        status=Vehicle.Status.AVAILABLE,
        published_at=timezone.now(),
        price=Decimal("35000.00"),
        short_description="Vehículo QA disponible",
    )
    test_case.customer = Customer.objects.create(
        first_name="Elena",
        last_name="Pruebas",
        identification_number="0912345678",
        email="elena.qa@example.com",
        phone="0999999999",
        assigned_branch=test_case.branch,
        assigned_advisor=test_case.admin,
    )
    test_case.category = InventoryCategory.objects.create(name="Accesorios QA", slug="accesorios-qa")
    test_case.item = InventoryItem.objects.create(
        category=test_case.category,
        name="Kit QA",
        sku="KIT-QA-001",
        item_type=InventoryItem.ItemType.ACCESSORY,
        price=Decimal("80.00"),
        cost=Decimal("50.00"),
    )
