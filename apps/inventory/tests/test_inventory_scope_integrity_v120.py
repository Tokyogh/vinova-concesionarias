"""ES: Este módulo especifica regresiones ejecutables para el dominio de inventario.

EN: This module specifies executable regressions for the inventory domain.

Contexto existente / Existing context:
Regression coverage for inventory scope integrity v120 in the inventory domain.
"""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.inventory.models import BranchStock, InventoryCategory, InventoryItem, StockMovement
from apps.inventory.services import record_stock_movement, transfer_stock


def inventory_scope_context(django_user_model):
    company = Company.objects.create(
        legal_name="Inventario Scope S.A.",
        commercial_name="Inventario Scope",
        ruc="1799999999027",
    )
    own_branch = Branch.objects.create(
        company=company,
        name="Bodega Scope Norte",
        code="STK-NORTE",
        city="Quito",
    )
    other_branch = Branch.objects.create(
        company=company,
        name="Bodega Scope Sur",
        code="STK-SUR",
        city="Loja",
    )
    permissions = [
        PermissionCode.objects.create(module="inventory", code=code, name=code)
        for code in ("inventory.view", "inventory.manage_stock")
    ]
    role = Role.objects.create(code="stock_scope_norte", name="Stock scope norte")
    role.permissions.add(*permissions)
    user = django_user_model.objects.create_user(
        username="stock-scope-norte",
        email="stock-scope@example.com",
        password="x",
    )
    UserRole.objects.create(user=user, role=role, branch=own_branch)
    category = InventoryCategory.objects.create(name="Scope Stock", slug="scope-stock")
    item = InventoryItem.objects.create(
        category=category,
        name="Repuesto scoped",
        sku="STK-SCOPE-001",
        price=Decimal("20.00"),
    )
    own_stock = BranchStock.objects.create(
        item=item,
        branch=own_branch,
        quantity=Decimal("5.00"),
    )
    other_stock = BranchStock.objects.create(
        item=item,
        branch=other_branch,
        quantity=Decimal("90.00"),
    )
    StockMovement.objects.create(
        item=item,
        branch=own_branch,
        movement_type=StockMovement.MovementType.IN,
        quantity=Decimal("5.00"),
        previous_quantity=Decimal("0.00"),
        new_quantity=Decimal("5.00"),
        confirmed_at=timezone.now(),
    )
    StockMovement.objects.create(
        item=item,
        branch=other_branch,
        movement_type=StockMovement.MovementType.IN,
        quantity=Decimal("90.00"),
        previous_quantity=Decimal("0.00"),
        new_quantity=Decimal("90.00"),
        confirmed_at=timezone.now(),
    )
    return user, own_branch, other_branch, item, own_stock, other_stock


@pytest.mark.django_db
def test_inventory_html_api_totals_stock_and_movements_are_branch_scoped(client, django_user_model):
    user, own_branch, other_branch, item, own_stock, other_stock = inventory_scope_context(django_user_model)
    client.force_login(user)

    html = client.get("/dashboard/inventory/")
    assert html.status_code == 200
    assert item.sku.encode() in html.content
    assert own_branch.name.encode() in html.content
    assert other_branch.name.encode() not in html.content

    stock_api = client.get("/api/v1/inventory-stock/")
    assert stock_api.status_code == 200
    stock_rows = stock_api.data.get("results", stock_api.data)
    assert {row["id"] for row in stock_rows} == {own_stock.pk}

    item_api = client.get(f"/api/v1/inventory-items/{item.pk}/")
    assert item_api.status_code == 200
    assert Decimal(item_api.data["total_stock"]) == Decimal("5.00")

    movement_api = client.get("/api/v1/inventory-movements/")
    assert movement_api.status_code == 200
    assert own_branch.name in str(movement_api.data)
    assert other_branch.name not in str(movement_api.data)


@pytest.mark.django_db
def test_inventory_mutations_require_permission_on_every_affected_branch(client, django_user_model):
    user, _, other_branch, item, _, other_stock = inventory_scope_context(django_user_model)
    client.force_login(user)

    response = client.post(
        "/api/v1/inventory-movements/",
        {
            "item": item.pk,
            "branch": other_branch.pk,
            "movement_type": StockMovement.MovementType.OUT,
            "quantity": "1.00",
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    other_stock.refresh_from_db()
    assert other_stock.quantity == Decimal("90.00")


@pytest.mark.django_db
def test_stock_settings_route_cannot_update_another_branch(client, django_user_model):
    user, _, _, item, _, other_stock = inventory_scope_context(django_user_model)
    client.force_login(user)

    response = client.post(
        f"/dashboard/inventory/{item.pk}/stock/{other_stock.pk}/settings/",
        {"minimum_stock": "25.00", "location_code": "AJENA-01"},
    )

    assert response.status_code == 404
    other_stock.refresh_from_db()
    assert other_stock.minimum_stock == Decimal("0.00")
    assert other_stock.location_code == ""


@pytest.mark.django_db
@pytest.mark.parametrize("operation", ["out", "adjust", "transfer"])
def test_manual_stock_operations_cannot_consume_commercial_reservations(
    django_user_model,
    operation,
):
    user, own_branch, other_branch, item, own_stock, other_stock = inventory_scope_context(django_user_model)
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    own_stock.quantity = Decimal("10.00")
    own_stock.reserved_quantity = Decimal("4.00")
    own_stock.save(update_fields=["quantity", "reserved_quantity", "updated_at"])

    with pytest.raises(ValidationError):
        if operation == "out":
            record_stock_movement(
                actor=user,
                item=item,
                branch=own_branch,
                movement_type=StockMovement.MovementType.OUT,
                quantity=Decimal("7.00"),
            )
        elif operation == "adjust":
            record_stock_movement(
                actor=user,
                item=item,
                branch=own_branch,
                movement_type=StockMovement.MovementType.ADJUST,
                quantity=Decimal("3.00"),
            )
        else:
            transfer_stock(
                actor=user,
                item=item,
                origin_branch=own_branch,
                destination_branch=other_branch,
                quantity=Decimal("7.00"),
            )

    own_stock.refresh_from_db()
    other_stock.refresh_from_db()
    assert own_stock.quantity == Decimal("10.00")
    assert own_stock.reserved_quantity == Decimal("4.00")
    assert other_stock.quantity == Decimal("90.00")


@pytest.mark.django_db
def test_database_rejects_reserved_stock_above_physical_quantity(django_user_model):
    _, _, _, _, own_stock, _ = inventory_scope_context(django_user_model)

    with pytest.raises(IntegrityError), transaction.atomic():
        BranchStock.objects.filter(pk=own_stock.pk).update(
            quantity=Decimal("2.00"),
            reserved_quantity=Decimal("3.00"),
        )


@pytest.mark.django_db
def test_inventory_admin_cannot_bypass_stock_services(client, django_user_model):
    user, _, _, item, own_stock, _ = inventory_scope_context(django_user_model)
    user.is_staff = True
    user.is_superuser = True
    user.save(update_fields=["is_staff", "is_superuser"])
    client.force_login(user)

    assert client.get("/admin/inventory/branchstock/add/").status_code == 403
    stock_page = client.get(f"/admin/inventory/branchstock/{own_stock.pk}/change/")
    assert stock_page.status_code == 200
    assert b'name="quantity"' not in stock_page.content
    movement = item.movements.first()
    movement_page = client.get(f"/admin/inventory/stockmovement/{movement.pk}/change/")
    assert movement_page.status_code == 200
    assert b'name="status"' not in movement_page.content
    assert b'name="quantity"' not in movement_page.content
