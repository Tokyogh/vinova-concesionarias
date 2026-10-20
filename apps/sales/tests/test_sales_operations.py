"""ES: Este módulo especifica regresiones ejecutables para el dominio de ventas.

EN: This module specifies executable regressions for the sales domain.

Contexto existente / Existing context:
Regression coverage for sales operations in the sales domain.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.inventory.models import BranchStock, InventoryCategory, InventoryItem, StockMovement
from apps.inventory.services import record_stock_movement
from apps.sales.models import SaleLine, SaleRecord
from apps.sales.services import confirm_sale, create_status_history, recalculate_sale_totals, reserve_sale
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel


@pytest.fixture
def sales_permissions():
    perms = {}
    for code in [
        "dashboard.view",
        "sales.quote",
        "sales.reserve",
        "sales.sell",
        "customers.view",
        "vehicles.view",
        "inventory.view",
    ]:
        perms[code] = PermissionCode.objects.create(module=code.split(".")[0], code=code, name=code)
    return perms


@pytest.fixture
def sales_manager(django_user_model, sales_permissions):
    user = django_user_model.objects.create_user(
        username="salesmanager", email="salesmanager@example.com", password="x"
    )
    role = Role.objects.create(code="gerente_comercial", name="Gerente comercial")
    role.permissions.add(*sales_permissions.values())
    UserRole.objects.create(user=user, role=role)
    return user


@pytest.fixture
def branch():
    company = Company.objects.create(legal_name="Ventas Demo S.A.", commercial_name="Ventas Demo", ruc="1790000000088")
    return Branch.objects.create(
        company=company, name="Sucursal Ventas", code="SALE-001", branch_type=Branch.BranchType.DEALERSHIP, city="Quito"
    )


@pytest.fixture
def customer(branch, sales_manager):
    return Customer.objects.create(
        first_name="Carlos",
        last_name="Mendoza",
        identification_number="0912340000",
        assigned_branch=branch,
        assigned_advisor=sales_manager,
    )


@pytest.fixture
def vehicle(branch):
    brand = VehicleBrand.objects.create(name="GMC")
    model = VehicleModel.objects.create(brand=brand, name="Canyon")
    return Vehicle.objects.create(
        brand=brand,
        model=model,
        branch=branch,
        year=2023,
        version="AT4X",
        vin="VINSALE0001",
        public_slug="gmc-canyon-sale",
        status=Vehicle.Status.AVAILABLE,
        price="65000.00",
    )


@pytest.fixture
def inventory_item(branch):
    category = InventoryCategory.objects.create(name="Accesorios", slug="accesorios-sales")
    item = InventoryItem.objects.create(
        category=category,
        name="Kit alfombras",
        sku="ACC-SALE-001",
        item_type=InventoryItem.ItemType.ACCESSORY,
        price="80.00",
    )
    record_stock_movement(
        actor=None,
        item=item,
        branch=branch,
        movement_type=StockMovement.MovementType.IN,
        quantity=Decimal("5"),
        reference="TEST-STOCK",
    )
    return item


@pytest.mark.django_db
def test_internal_sales_module_requires_login(client):
    response = client.get("/dashboard/sales/")
    assert response.status_code == 302
    assert "/accounts/login/" in response.headers["Location"]


@pytest.mark.django_db
def test_common_user_cannot_access_internal_sales_module(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="clientesales", email="clientesales@example.com", password="x"
    )
    client.force_login(user)
    response = client.get("/dashboard/sales/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_sales_manager_can_create_quote_from_view(client, sales_manager, branch, customer, vehicle):
    client.force_login(sales_manager)
    response = client.post(
        "/dashboard/sales/new/",
        {
            "kind": SaleRecord.Kind.QUOTE,
            "customer": customer.pk,
            "branch": branch.pk,
            "advisor": sales_manager.pk,
            "vehicle": vehicle.pk,
            "source": SaleRecord.Source.SHOWROOM,
            "vehicle_price": "65000.00",
            "vehicle_discount": "500.00",
            "tax_rate": "15.00",
            "valid_until": (timezone.localdate() + timedelta(days=7)).isoformat(),
            "notes": "Cotización de prueba",
            "internal_notes": "Seguimiento comercial",
        },
    )
    sale = SaleRecord.objects.get(customer=customer)
    assert response.status_code == 302
    assert response.headers["Location"] == f"/dashboard/sales/{sale.pk}/"
    assert sale.number.startswith("COT-")
    assert sale.status == SaleRecord.Status.QUOTED
    assert sale.total == Decimal("74175.00")


@pytest.mark.django_db
def test_reserve_sale_updates_vehicle_and_reserved_stock(sales_manager, branch, customer, vehicle, inventory_item):
    sale = SaleRecord.objects.create(
        number="COT-TEST-0001",
        kind=SaleRecord.Kind.QUOTE,
        status=SaleRecord.Status.QUOTED,
        customer=customer,
        branch=branch,
        advisor=sales_manager,
        vehicle=vehicle,
        vehicle_price=vehicle.price,
    )
    create_status_history(sale=sale, new=sale.status, actor=sales_manager)
    line = SaleLine.objects.create(
        sale=sale,
        item=inventory_item,
        description=inventory_item.name,
        quantity=Decimal("2"),
        unit_price=inventory_item.price,
    )
    line.calculate_totals()
    line.save()
    recalculate_sale_totals(sale)

    reserve_sale(actor=sales_manager, sale=sale, reserved_until=timezone.now() + timedelta(days=2), note="Reserva test")

    vehicle.refresh_from_db()
    line.refresh_from_db()
    stock = BranchStock.objects.get(item=inventory_item, branch=branch)
    sale.refresh_from_db()
    assert sale.status == SaleRecord.Status.RESERVED
    assert vehicle.status == Vehicle.Status.RESERVED
    assert stock.reserved_quantity == Decimal("2.00")
    assert line.reserved_quantity == Decimal("2.00")


@pytest.mark.django_db
def test_confirm_sale_marks_vehicle_sold_and_deducts_stock(sales_manager, branch, customer, vehicle, inventory_item):
    sale = SaleRecord.objects.create(
        number="RES-TEST-0001",
        kind=SaleRecord.Kind.RESERVATION,
        status=SaleRecord.Status.QUOTED,
        customer=customer,
        branch=branch,
        advisor=sales_manager,
        vehicle=vehicle,
        vehicle_price=vehicle.price,
    )
    line = SaleLine.objects.create(
        sale=sale,
        item=inventory_item,
        description=inventory_item.name,
        quantity=Decimal("2"),
        unit_price=inventory_item.price,
    )
    line.calculate_totals()
    line.save()
    recalculate_sale_totals(sale)
    reserve_sale(
        actor=sales_manager, sale=sale, reserved_until=timezone.now() + timedelta(days=2), note="Reserva previa"
    )

    confirm_sale(actor=sales_manager, sale=sale, note="Venta test")

    vehicle.refresh_from_db()
    line.refresh_from_db()
    sale.refresh_from_db()
    stock = BranchStock.objects.get(item=inventory_item, branch=branch)
    assert sale.status == SaleRecord.Status.SOLD
    assert vehicle.status == Vehicle.Status.SOLD
    assert stock.quantity == Decimal("3.00")
    assert stock.reserved_quantity == Decimal("0.00")
    assert line.fulfilled_quantity == Decimal("2.00")


@pytest.mark.django_db
def test_sidebar_points_to_internal_sales(client, sales_manager):
    client.force_login(sales_manager)
    response = client.get("/dashboard/", follow=True)
    assert response.status_code == 200
    assert b"/dashboard/sales/" in response.content
    assert b"Ventas <span>Pr" not in response.content
