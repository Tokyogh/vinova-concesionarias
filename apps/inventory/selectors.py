"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de inventario.

EN: This module implements authorization-aware read queries for the inventory domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the inventory domain.
"""

from __future__ import annotations

from django.db.models import Count, Exists, F, OuterRef, Prefetch, Q, Sum

from apps.accounts.scopes import accessible_branch_ids
from apps.inventory.models import (
    PUBLIC_CATALOG_ITEM_TYPES,
    BranchStock,
    InventoryCategory,
    InventoryItem,
    StockMovement,
)

INVENTORY_SCOPE_PERMISSIONS = ("inventory.view", "inventory.manage_stock")


def _inventory_branch_ids(user, *, permission_codes=INVENTORY_SCOPE_PERMISSIONS):
    return accessible_branch_ids(user, permission_codes=permission_codes)


def _scope_stock_queryset(qs, *, user, permission_codes=INVENTORY_SCOPE_PERMISSIONS):
    branch_ids = _inventory_branch_ids(user, permission_codes=permission_codes)
    return qs if branch_ids is None else qs.filter(branch_id__in=branch_ids)


def _scope_movement_queryset(qs, *, user, permission_codes=INVENTORY_SCOPE_PERMISSIONS):
    branch_ids = _inventory_branch_ids(user, permission_codes=permission_codes)
    if branch_ids is None:
        return qs
    return qs.filter(Q(branch_id__in=branch_ids) | Q(destination_branch_id__in=branch_ids))


def inventory_item_queryset(*, user, query: str = "", status: str = "", item_type: str = "", category=None, sort: str = ""):
    branch_ids = _inventory_branch_ids(user)
    stock_filter = Q() if branch_ids is None else Q(stock_records__branch_id__in=branch_ids)
    low_stock = BranchStock.objects.filter(
        item_id=OuterRef("pk"),
        minimum_stock__gt=0,
        quantity__lte=F("minimum_stock"),
    )
    if branch_ids is not None:
        low_stock = low_stock.filter(branch_id__in=branch_ids)
    qs = (
        InventoryItem.objects.filter(is_deleted=False)
        .select_related("category", "created_by")
        .annotate(
            total_stock_amount=Sum("stock_records__quantity", filter=stock_filter),
            branch_count=Count("stock_records", filter=stock_filter, distinct=True),
            has_low_stock_scoped=Exists(low_stock),
        )
    )
    if query:
        qs = qs.filter(Q(name__icontains=query) | Q(sku__icontains=query) | Q(description__icontains=query) | Q(category__name__icontains=query))
    if status:
        qs = qs.filter(status=status)
    if item_type:
        qs = qs.filter(item_type=item_type)
    if category:
        qs = qs.filter(category=category)
    ordering = {
        "name_desc": ("-name",), "stock_desc": ("-total_stock_amount", "name"),
        "stock_asc": ("total_stock_amount", "name"), "newest": ("-created_at",),
    }.get(sort, ("name",))
    return qs.order_by(*ordering)


def active_categories_queryset():
    return InventoryCategory.objects.filter(is_active=True).select_related("parent").order_by("name")


def public_inventory_categories_queryset():
    """ES: Categorías con artículos publicados. EN: Categories with published items."""

    return (
        InventoryCategory.objects.filter(
            is_active=True,
            items__is_deleted=False,
            items__status=InventoryItem.Status.ACTIVE,
            items__is_public=True,
            items__item_type__in=PUBLIC_CATALOG_ITEM_TYPES,
        )
        .distinct()
        .order_by("name")
    )


def public_inventory_item_queryset(*, query: str = "", category_slug: str = "", item_type: str = "", sort: str = ""):
    """ES: Proyecta solo información publicable. EN: Projects only publishable information."""

    public_stock = (
        BranchStock.objects.filter(
            quantity__gt=F("reserved_quantity"),
            branch__is_active=True,
            branch__is_public=True,
            branch__company__is_active=True,
        )
        .select_related("branch")
        .only("id", "item_id", "branch__id", "branch__name", "branch__city")
        .order_by("branch__name")
    )
    queryset = (
        InventoryItem.objects.filter(
            is_deleted=False,
            status=InventoryItem.Status.ACTIVE,
            is_public=True,
            item_type__in=PUBLIC_CATALOG_ITEM_TYPES,
        )
        .select_related("category")
        .prefetch_related(Prefetch("stock_records", queryset=public_stock, to_attr="public_stock_records"))
    )
    if query:
        queryset = queryset.filter(
            Q(name__icontains=query)
            | Q(sku__icontains=query)
            | Q(description__icontains=query)
            | Q(category__name__icontains=query)
        )
    if category_slug:
        queryset = queryset.filter(category__slug=category_slug)
    if item_type:
        queryset = queryset.filter(item_type=item_type)
    ordering = {
        "name": ("name", "pk"),
        "price_asc": ("price", "name", "pk"),
        "price_desc": ("-price", "name", "pk"),
    }.get(sort, ("-updated_at", "-pk"))
    return queryset.order_by(*ordering)


def inventory_item_detail_queryset(user):
    stock_qs = _scope_stock_queryset(BranchStock.objects.select_related("branch"), user=user)
    return (
        InventoryItem.objects.filter(is_deleted=False)
        .select_related("category", "created_by")
        .prefetch_related(Prefetch("stock_records", queryset=stock_qs))
    )


def stock_by_branch_queryset(*, user, item=None, branch=None, permission_codes=INVENTORY_SCOPE_PERMISSIONS):
    qs = _scope_stock_queryset(
        BranchStock.objects.select_related("item", "branch", "item__category").filter(item__is_deleted=False),
        user=user,
        permission_codes=permission_codes,
    )
    if item is not None:
        qs = qs.filter(item=item)
    if branch is not None:
        qs = qs.filter(branch=branch)
    return qs.order_by("branch__company__commercial_name", "branch__name", "item__name")


def low_stock_queryset(user):
    return (
        _scope_stock_queryset(
            BranchStock.objects.select_related("item", "item__category", "branch", "branch__company"),
            user=user,
        )
        .filter(item__is_deleted=False, item__status=InventoryItem.Status.ACTIVE, item__track_stock=True, minimum_stock__gt=0, quantity__lte=F("minimum_stock"))
        .order_by("quantity", "item__name")
    )



def stock_movements_queryset(*, user, item=None, branch=None, movement_type: str = "", query: str = ""):
    qs = _scope_movement_queryset(
        StockMovement.objects.select_related("item", "branch", "destination_branch", "created_by", "item__category"),
        user=user,
    )
    if item is not None:
        qs = qs.filter(item=item)
    if branch is not None:
        qs = qs.filter(Q(branch=branch) | Q(destination_branch=branch))
    if movement_type:
        qs = qs.filter(movement_type=movement_type)
    if query:
        qs = qs.filter(Q(item__sku__icontains=query) | Q(item__name__icontains=query) | Q(reference__icontains=query) | Q(reason__icontains=query))
    return qs.order_by("-confirmed_at", "-created_at")


def inventory_metrics(user):
    stock_qs = _scope_stock_queryset(
        BranchStock.objects.filter(item__is_deleted=False, item__track_stock=True),
        user=user,
    )
    low_qs = stock_qs.filter(minimum_stock__gt=0, quantity__lte=F("minimum_stock"))
    return {
        "active_items": InventoryItem.objects.filter(is_deleted=False, status=InventoryItem.Status.ACTIVE).count(),
        "archived_items": InventoryItem.objects.filter(is_deleted=False, status=InventoryItem.Status.ARCHIVED).count(),
        "total_stock": stock_qs.aggregate(total=Sum("quantity"))["total"] or 0,
        "low_stock": low_qs.count(),
        "branches_with_stock": stock_qs.values("branch").distinct().count(),
        "recent_movements": _scope_movement_queryset(
            StockMovement.objects.filter(status=StockMovement.Status.CONFIRMED),
            user=user,
        ).count(),
    }
