"""ES: Este módulo especifica regresiones ejecutables para el dominio de ventas.

EN: This module specifies executable regressions for the sales domain.

Contexto existente / Existing context:
Regression coverage for sales query count v200 in the sales domain.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.sales.models import SaleRecord
from apps.sales.selectors import sale_list_queryset
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel


@pytest.fixture
def perf_sales_context(django_user_model):
    company = Company.objects.create(legal_name="Perf Sales S.A.", commercial_name="Perf Sales", ruc="1790000000044")
    branch = Branch.objects.create(company=company, name="Matriz", code="PERF-S", city="Quito")
    user = django_user_model.objects.create_user(username="perf-sales", email="perf-sales@example.com", password="x")
    perms = [
        PermissionCode.objects.create(module=code.split(".")[0], code=code, name=code)
        for code in ["sales.quote", "sales.reserve", "sales.sell"]
    ]
    role = Role.objects.create(code="perf-sales", name="Perf sales")
    role.permissions.add(*perms)
    UserRole.objects.create(user=user, role=role)
    brand = VehicleBrand.objects.create(name="Perf Brand")
    model_ = VehicleModel.objects.create(brand=brand, name="Perf Model")
    for i in range(20):
        vehicle = Vehicle.objects.create(
            brand=brand, model=model_, branch=branch, year=2026, vin=f"SVIN{i:04d}",
            public_slug=f"perf-sale-veh-{i}", price=Decimal("20000.00"), status=Vehicle.Status.AVAILABLE,
        )
        customer = Customer.objects.create(
            first_name=f"Cliente {i}", identification_number=f"18{i:06d}", assigned_branch=branch, assigned_advisor=user,
        )
        SaleRecord.objects.create(
            number=f"PS-{i:04d}", kind=SaleRecord.Kind.SALE, status=SaleRecord.Status.SOLD,
            customer=customer, branch=branch, vehicle=vehicle,
            vehicle_price=Decimal("20000.00"), total=Decimal("23000.00"), balance_due=Decimal("0.00"),
        )
    return user


@pytest.mark.django_db
def test_sale_list_queryset_prefetches_vehicle_model_brand_no_n_plus_one(perf_sales_context):
    sales = list(sale_list_queryset(perf_sales_context))
    assert sales
    with CaptureQueriesContext(connection) as ctx:
        for sale in sales:
            if sale.vehicle:
                str(sale.vehicle)
    brand_queries = [q for q in ctx.captured_queries if "vehicles_vehiclebrand" in q["sql"]]
    assert len(brand_queries) == 0, (
        f"Se detectó N+1 en `str(vehicle)`: {len(brand_queries)} consultas a vehiclebrand "
        f"para {len(sales)} ventas (esperado 0 vía select_related)."
    )
