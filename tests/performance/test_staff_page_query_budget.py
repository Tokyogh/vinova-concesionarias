# -*- coding: utf-8 -*-
"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Presupuesto de consultas SQL por página staff (auditoría de rendimiento D7).

Mide el número de queries ejecutadas al renderizar las páginas staff críticas
con un volumen moderado de datos (30 clientes, 30 vehículos, 30 ítems) y falla
si alguna página se pasa de su presupuesto: es la señal habitual de un N+1.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.management import call_command
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.accounts.models import Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.inventory.models import InventoryCategory, InventoryItem
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel

pytestmark = pytest.mark.django_db

ROW_COUNT = 30

# (id, path, presupuesto máximo de queries)
STAFF_PAGES = [
    ("home", "/dashboard/", 45),
    ("admin", "/dashboard/admin/", 45),
    ("branch", "/dashboard/branch/", 45),
    ("commercial", "/dashboard/commercial/", 45),
    ("seller", "/dashboard/seller/", 45),
    ("inventory_home", "/dashboard/inventory-home/", 45),
    ("billing", "/dashboard/billing/", 45),
    ("support", "/dashboard/support/", 45),
    ("marketing", "/dashboard/marketing/", 45),
    ("auditor", "/dashboard/auditor/", 45),
    ("customers", "/dashboard/customers/", 45),
    ("vehicles", "/dashboard/vehicles/", 45),
    ("sales", "/dashboard/sales/", 45),
    ("invoices", "/dashboard/invoices/", 45),
    ("leads", "/dashboard/leads/", 45),
    ("inventory", "/dashboard/inventory/", 45),
    ("documents", "/dashboard/documents/", 45),
    ("notifications", "/dashboard/notifications/", 45),
    ("reports", "/dashboard/reports/", 45),
    ("analytics", "/dashboard/analytics/", 45),
    ("audit", "/dashboard/audit/", 45),
    ("imports", "/dashboard/imports/", 45),
    ("privacy", "/dashboard/privacy/", 45),
    ("security", "/dashboard/security/", 45),
]


def _seed(django_user_model):
    call_command("seed_roles", verbosity=0)

    company = Company.objects.create(
        legal_name="Vinova Perf S.A.",
        commercial_name="Vinova Perf",
        ruc="1799999999003",
    )
    branch = Branch.objects.create(
        company=company,
        name="Matriz Perf",
        code="PF-MTR",
        branch_type=Branch.BranchType.DEALERSHIP,
        city="Quito",
    )
    user = django_user_model.objects.create_superuser(
        username="perf-admin",
        email="perf-admin@example.com",
        password="Vinova-QA-Password-2026!",
        branch=branch,
    )
    UserRole.objects.create(user=user, role=Role.objects.get(code="superadmin"), branch=None)

    for index in range(1, ROW_COUNT + 1):
        Customer.objects.create(
            first_name=f"Cliente {index}",
            last_name="Presupuesto",
            identification_number=f"0999999{index:04d}",
            email=f"perf{index}@example.com",
            phone="0999999999",
            assigned_branch=branch,
            assigned_advisor=user,
        )

    brand = VehicleBrand.objects.create(name="Foton Perf")
    model = VehicleModel.objects.create(brand=brand, name="Tunland Perf")
    for index in range(1, ROW_COUNT + 1):
        Vehicle.objects.create(
            brand=brand,
            model=model,
            branch=branch,
            year=2026,
            version="G7",
            vin=f"VINPERF{index:013d}",
            public_slug=f"perf-vehicle-{index}",
            status=Vehicle.Status.AVAILABLE,
            published_at=timezone.now(),
            price=Decimal("35000.00"),
            short_description="Vehículo de presupuesto",
        )

    category = InventoryCategory.objects.create(name="Accesorios Perf", slug="accesorios-perf")
    for index in range(1, ROW_COUNT + 1):
        InventoryItem.objects.create(
            category=category,
            name=f"Kit Perf {index}",
            sku=f"KIT-PERF-{index:03d}",
            item_type=InventoryItem.ItemType.ACCESSORY,
            price=Decimal("80.00"),
            cost=Decimal("50.00"),
        )

    return user


def test_staff_pages_stay_within_query_budget(django_user_model, client):
    user = _seed(django_user_model)
    client.force_login(user)

    measurements = {}
    over_budget = []

    for page_id, path, budget in STAFF_PAGES:
        with CaptureQueriesContext(connection) as context:
            response = client.get(path)

        assert response.status_code == 200, f"{path} devolvió {response.status_code}"

        count = len(context.captured_queries)
        measurements[page_id] = count
        if count > budget:
            over_budget.append(f"{path}: {count} queries (presupuesto {budget})")

    print("queries por página:", measurements)

    assert not over_budget, "Páginas fuera de presupuesto:\n" + "\n".join(over_budget)
    assert measurements, "no se midió ninguna página"
