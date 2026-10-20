"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de inventario.

EN: This module implements business services and transactional effects for the inventory domain.

Contexto existente / Existing context:
Transactional business services for the inventory domain.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services import audit_log
from apps.inventory.models import BranchStock, InventoryCategory, InventoryItem, StockMovement


def _require_stock_permission(*, actor, branch) -> None:
    if actor is not None and not actor.has_perm_code("inventory.manage_stock", branch=branch):
        raise ValidationError("No tienes permiso para gestionar stock en esta sucursal.")


def _item_snapshot(item: InventoryItem) -> dict:
    return {
        "sku": item.sku,
        "name": item.name,
        "item_type": item.item_type,
        "category": item.category_id,
        "price": str(item.price),
        "cost": str(item.cost) if item.cost is not None else None,
        "status": item.status,
        "track_stock": item.track_stock,
        "is_public": item.is_public,
    }


def _movement_snapshot(movement: StockMovement) -> dict:
    return {
        "item": movement.item_id,
        "branch": movement.branch_id,
        "destination_branch": movement.destination_branch_id,
        "movement_type": movement.movement_type,
        "quantity": str(movement.quantity),
        "previous_quantity": str(movement.previous_quantity),
        "new_quantity": str(movement.new_quantity),
        "destination_previous_quantity": str(movement.destination_previous_quantity) if movement.destination_previous_quantity is not None else None,
        "destination_new_quantity": str(movement.destination_new_quantity) if movement.destination_new_quantity is not None else None,
        "reference": movement.reference,
    }


@transaction.atomic
def create_inventory_category(*, actor, form) -> InventoryCategory:
    category = form.save()
    audit_log(user=actor, action="inventory.category_create", target=category, after={"name": category.name, "slug": category.slug})
    return category


@transaction.atomic
def create_inventory_item(*, actor, form) -> InventoryItem:
    item = form.save(commit=False)
    item.created_by = actor if getattr(actor, "is_authenticated", False) else None
    item.save()
    form.save_m2m()
    audit_log(user=actor, action="inventory.item_create", target=item, after=_item_snapshot(item))
    return item


@transaction.atomic
def update_inventory_item(*, actor, item: InventoryItem, form) -> InventoryItem:
    before = _item_snapshot(item)
    item = form.save(commit=False)
    item.save()
    form.save_m2m()
    audit_log(user=actor, action="inventory.item_update", target=item, before=before, after=_item_snapshot(item))
    return item


@transaction.atomic
def archive_inventory_item(*, actor, item: InventoryItem) -> InventoryItem:
    before = _item_snapshot(item)
    item.status = InventoryItem.Status.ARCHIVED
    item.is_public = False
    item.save(update_fields=["status", "is_public", "updated_at"])
    audit_log(user=actor, action="inventory.item_archive", target=item, before=before, after=_item_snapshot(item))
    return item


@transaction.atomic
def activate_inventory_item(*, actor, item: InventoryItem) -> InventoryItem:
    before = _item_snapshot(item)
    item.status = InventoryItem.Status.ACTIVE
    item.is_deleted = False
    item.deleted_at = None
    item.save(update_fields=["status", "is_deleted", "deleted_at", "updated_at"])
    audit_log(user=actor, action="inventory.item_activate", target=item, before=before, after=_item_snapshot(item))
    return item


def _stock_record_for_update(*, item: InventoryItem, branch):
    record = BranchStock.objects.select_for_update().filter(item=item, branch=branch).first()
    if record:
        return record
    try:
        with transaction.atomic():
            return BranchStock.objects.create(item=item, branch=branch)
    except IntegrityError:
        return BranchStock.objects.select_for_update().get(item=item, branch=branch)


def _ensure_stock_record(*, item: InventoryItem, branch):
    record = BranchStock.objects.filter(item=item, branch=branch).first()
    if record:
        return record
    try:
        with transaction.atomic():
            return BranchStock.objects.create(item=item, branch=branch)
    except IntegrityError:
        return BranchStock.objects.get(item=item, branch=branch)


def _normalize_quantity(value) -> Decimal:
    quantity = Decimal(value)
    if quantity <= 0:
        raise ValidationError("La cantidad debe ser mayor a cero.")
    return quantity


@transaction.atomic
def record_stock_movement(*, actor, item: InventoryItem, branch, movement_type: str, quantity, reference: str = "", reason: str = "", unit_cost=None) -> StockMovement:
    _require_stock_permission(actor=actor, branch=branch)
    if not item.track_stock:
        raise ValidationError("Este artículo no maneja stock físico.")
    quantity = _normalize_quantity(quantity)
    record = _stock_record_for_update(item=item, branch=branch)
    previous = record.quantity

    if movement_type == StockMovement.MovementType.IN:
        new_quantity = previous + quantity
    elif movement_type == StockMovement.MovementType.OUT:
        new_quantity = previous - quantity
        if new_quantity < record.reserved_quantity:
            raise ValidationError("La salida consumiría stock reservado por operaciones comerciales.")
    elif movement_type == StockMovement.MovementType.ADJUST:
        new_quantity = quantity
        if new_quantity < record.reserved_quantity:
            raise ValidationError("El ajuste no puede dejar el stock por debajo de la cantidad reservada.")
    else:
        raise ValidationError("Tipo de movimiento no soportado desde este formulario.")

    now = timezone.now()
    record.quantity = new_quantity
    record.last_movement_at = now
    record.save(update_fields=["quantity", "last_movement_at", "updated_at"])

    movement = StockMovement.objects.create(
        item=item,
        branch=branch,
        movement_type=movement_type,
        quantity=quantity,
        previous_quantity=previous,
        new_quantity=new_quantity,
        unit_cost=unit_cost or None,
        reference=reference,
        reason=reason,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        confirmed_at=now,
    )
    audit_log(user=actor, action=f"inventory.stock_{movement_type}", target=item, branch=branch, after=_movement_snapshot(movement))
    return movement


@transaction.atomic
def transfer_stock(*, actor, item: InventoryItem, origin_branch, destination_branch, quantity, reference: str = "", reason: str = "") -> StockMovement:
    if destination_branch is None:
        raise ValidationError("Una transferencia requiere sucursal destino.")
    if origin_branch == destination_branch:
        raise ValidationError("La sucursal destino debe ser diferente a la sucursal origen.")
    _require_stock_permission(actor=actor, branch=origin_branch)
    _require_stock_permission(actor=actor, branch=destination_branch)
    if not item.track_stock:
        raise ValidationError("Este artículo no maneja stock físico.")
    quantity = _normalize_quantity(quantity)

    seeds = {
        branch.pk: _ensure_stock_record(item=item, branch=branch)
        for branch in sorted((origin_branch, destination_branch), key=lambda candidate: candidate.pk)
    }
    origin_seed = seeds[origin_branch.pk]
    destination_seed = seeds[destination_branch.pk]
    locked_records = {
        record.branch_id: record
        for record in BranchStock.objects.select_for_update()
        .filter(pk__in=(origin_seed.pk, destination_seed.pk))
        .order_by("pk")
    }
    origin_record = locked_records[origin_branch.pk]
    destination_record = locked_records[destination_branch.pk]

    origin_previous = origin_record.quantity
    destination_previous = destination_record.quantity
    origin_new = origin_previous - quantity
    if origin_new < origin_record.reserved_quantity:
        raise ValidationError("La transferencia consumiría stock reservado en la sucursal origen.")
    destination_new = destination_previous + quantity

    now = timezone.now()
    origin_record.quantity = origin_new
    origin_record.last_movement_at = now
    origin_record.save(update_fields=["quantity", "last_movement_at", "updated_at"])
    destination_record.quantity = destination_new
    destination_record.last_movement_at = now
    destination_record.save(update_fields=["quantity", "last_movement_at", "updated_at"])

    movement = StockMovement.objects.create(
        item=item,
        branch=origin_branch,
        destination_branch=destination_branch,
        movement_type=StockMovement.MovementType.TRANSFER,
        quantity=quantity,
        previous_quantity=origin_previous,
        new_quantity=origin_new,
        destination_previous_quantity=destination_previous,
        destination_new_quantity=destination_new,
        reference=reference,
        reason=reason,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        confirmed_at=now,
    )
    audit_log(user=actor, action="inventory.stock_transfer", target=item, branch=origin_branch, after=_movement_snapshot(movement))
    return movement


@transaction.atomic
def update_minimum_stock(*, actor, stock: BranchStock, minimum_stock, location_code: str = "") -> BranchStock:
    stock = BranchStock.objects.select_for_update().select_related("branch", "item").get(pk=stock.pk)
    _require_stock_permission(actor=actor, branch=stock.branch)
    before = {"minimum_stock": str(stock.minimum_stock), "location_code": stock.location_code}
    stock.minimum_stock = Decimal(minimum_stock or 0)
    stock.location_code = location_code
    stock.full_clean()
    stock.save(update_fields=["minimum_stock", "location_code", "updated_at"])
    audit_log(user=actor, action="inventory.stock_settings_update", target=stock.item, before=before, after={"minimum_stock": str(stock.minimum_stock), "location_code": stock.location_code, "branch": stock.branch_id})
    return stock
