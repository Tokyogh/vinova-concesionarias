"""ES: Este módulo especifica regresiones ejecutables para el dominio de inventario.

EN: This module specifies executable regressions for the inventory domain.

Contexto existente / Existing context:
Regression coverage for inventory operations in the inventory domain.
"""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.audit.models import AuditLog
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.inventory.models import BranchStock, InventoryCategory, InventoryItem, StockMovement
from apps.inventory.services import record_stock_movement, transfer_stock


@pytest.fixture
def inventory_permissions():
    perms = {}
    for code in ["dashboard.view", "inventory.view", "inventory.manage_stock"]:
        perms[code] = PermissionCode.objects.create(module=code.split(".")[0], code=code, name=code)
    return perms


@pytest.fixture
def inventory_manager(django_user_model, inventory_permissions):
    user = django_user_model.objects.create_user(username="stockmanager", email="stockmanager@example.com", password="x")
    role = Role.objects.create(code="bodega", name="Bodega / stock")
    role.permissions.add(inventory_permissions["dashboard.view"], inventory_permissions["inventory.view"], inventory_permissions["inventory.manage_stock"])
    UserRole.objects.create(user=user, role=role)
    return user


@pytest.fixture
def branches():
    company = Company.objects.create(legal_name="Inventario Demo S.A.", commercial_name="Inventario Demo", ruc="1790000000014")
    b1 = Branch.objects.create(company=company, name="Matriz Norte", code="INV-001", branch_type=Branch.BranchType.WAREHOUSE, city="Quito")
    b2 = Branch.objects.create(company=company, name="Sucursal Sur", code="INV-002", branch_type=Branch.BranchType.DEALERSHIP, city="Guayaquil")
    return b1, b2


@pytest.fixture
def inventory_item():
    category = InventoryCategory.objects.create(name="Filtros", slug="filtros")
    return InventoryItem.objects.create(category=category, name="Filtro de aceite", sku="FIL-OIL-TST", item_type=InventoryItem.ItemType.FILTER, price="10.00")


@pytest.mark.django_db
def test_stock_movement_in_out_and_adjust(inventory_manager, inventory_item, branches):
    branch, _ = branches
    record_stock_movement(actor=inventory_manager, item=inventory_item, branch=branch, movement_type=StockMovement.MovementType.IN, quantity=Decimal("20"), reference="IN-1")
    record_stock_movement(actor=inventory_manager, item=inventory_item, branch=branch, movement_type=StockMovement.MovementType.OUT, quantity=Decimal("5"), reference="OUT-1")
    record_stock_movement(actor=inventory_manager, item=inventory_item, branch=branch, movement_type=StockMovement.MovementType.ADJUST, quantity=Decimal("12"), reference="ADJ-1")

    stock = BranchStock.objects.get(item=inventory_item, branch=branch)
    assert stock.quantity == Decimal("12.00")
    assert inventory_item.movements.count() == 3
    assert inventory_item.movements.latest("id").previous_quantity == Decimal("15.00")


@pytest.mark.django_db
def test_stock_cannot_go_negative(inventory_manager, inventory_item, branches):
    branch, _ = branches
    record_stock_movement(actor=inventory_manager, item=inventory_item, branch=branch, movement_type=StockMovement.MovementType.IN, quantity=Decimal("2"))
    with pytest.raises(ValidationError):
        record_stock_movement(actor=inventory_manager, item=inventory_item, branch=branch, movement_type=StockMovement.MovementType.OUT, quantity=Decimal("3"))


@pytest.mark.django_db
def test_transfer_stock_updates_origin_and_destination(inventory_manager, inventory_item, branches):
    origin, destination = branches
    record_stock_movement(actor=inventory_manager, item=inventory_item, branch=origin, movement_type=StockMovement.MovementType.IN, quantity=Decimal("30"))
    movement = transfer_stock(actor=inventory_manager, item=inventory_item, origin_branch=origin, destination_branch=destination, quantity=Decimal("7"), reference="TR-1")

    assert BranchStock.objects.get(item=inventory_item, branch=origin).quantity == Decimal("23.00")
    assert BranchStock.objects.get(item=inventory_item, branch=destination).quantity == Decimal("7.00")
    assert movement.destination_previous_quantity == Decimal("0.00")
    assert movement.destination_new_quantity == Decimal("7.00")


@pytest.mark.django_db
def test_internal_inventory_module_requires_login(client):
    response = client.get("/dashboard/inventory/")
    assert response.status_code == 302
    assert "/accounts/login/" in response.headers["Location"]


@pytest.mark.django_db
def test_common_user_cannot_access_internal_inventory_module(client, django_user_model):
    user = django_user_model.objects.create_user(username="clienteinv", email="clienteinv@example.com", password="x")
    client.force_login(user)
    response = client.get("/dashboard/inventory/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_inventory_manager_can_create_item_and_add_stock(client, inventory_manager, branches):
    branch, _ = branches
    category = InventoryCategory.objects.create(name="Aceites", slug="aceites")
    client.force_login(inventory_manager)

    response = client.post(
        "/dashboard/inventory/new/",
        {
            "category": category.pk,
            "name": "Aceite 5W-30",
            "sku": "OIL-5W30-TST",
            "item_type": InventoryItem.ItemType.OIL,
            "description": "Aceite sintético demo",
            "unit": "litro",
            "price": "12.50",
            "cost": "7.20",
            "status": InventoryItem.Status.ACTIVE,
            "track_stock": "on",
        },
    )
    item = InventoryItem.objects.get(sku="OIL-5W30-TST")
    assert response.status_code == 302
    assert response.headers["Location"] == f"/dashboard/inventory/{item.pk}/"

    stock_response = client.post(
        f"/dashboard/inventory/{item.pk}/stock/new/",
        {"item": item.pk, "branch": branch.pk, "movement_type": StockMovement.MovementType.IN, "quantity": "15", "reference": "TEST-IN", "reason": "Carga inicial"},
    )
    assert stock_response.status_code == 302
    assert BranchStock.objects.get(item=item, branch=branch).quantity == Decimal("15.00")


@pytest.mark.django_db
def test_inventory_manager_can_update_stock_replenishment_settings_from_item_detail(
    client,
    inventory_manager,
    inventory_item,
    branches,
):
    branch, _ = branches
    record_stock_movement(
        actor=inventory_manager,
        item=inventory_item,
        branch=branch,
        movement_type=StockMovement.MovementType.IN,
        quantity=Decimal("15"),
    )
    stock = BranchStock.objects.get(item=inventory_item, branch=branch)
    client.force_login(inventory_manager)

    response = client.post(
        f"/dashboard/inventory/{inventory_item.pk}/stock/{stock.pk}/settings/",
        {"minimum_stock": "8.50", "location_code": "PAS-A-04"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == f"/dashboard/inventory/{inventory_item.pk}/"
    stock.refresh_from_db()
    assert stock.minimum_stock == Decimal("8.50")
    assert stock.location_code == "PAS-A-04"
    audit = AuditLog.objects.get(action="inventory.stock_settings_update", object_id=str(inventory_item.pk))
    assert audit.before == {"minimum_stock": "0.00", "location_code": ""}
    assert audit.after["minimum_stock"] == "8.50"


@pytest.mark.django_db
def test_sidebar_points_to_internal_inventory(client, inventory_manager):
    client.force_login(inventory_manager)
    response = client.get("/dashboard/", follow=True)
    assert response.status_code == 200
    assert b"/dashboard/inventory/" in response.content
    assert b"Inventario <span>Pr" not in response.content
