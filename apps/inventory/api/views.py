"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de inventario.

EN: This module orchestrates HTTP requests, permissions, and responses for the inventory domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the inventory domain.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError as DRFValidationError
from rest_framework.response import Response

from apps.accounts.permissions import require_perm_code
from apps.audit.services import audit_log
from apps.inventory.api.serializers import BranchStockSerializer, InventoryCategorySerializer, InventoryItemSerializer, StockMovementSerializer
from apps.inventory.models import InventoryCategory, StockMovement
from apps.inventory.selectors import (
    inventory_item_queryset,
    low_stock_queryset,
    stock_by_branch_queryset,
    stock_movements_queryset,
)
from apps.inventory.services import record_stock_movement, transfer_stock


class InventoryReadManageMixin:
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        action = getattr(self, "action", None)
        if action in ["list", "retrieve", "low_stock"]:
            if not (request.user.has_perm_code("inventory.view") or request.user.has_perm_code("inventory.manage_stock")):
                raise PermissionDenied("No tienes permisos para consultar inventario.")
        else:
            require_perm_code(request.user, "inventory.manage_stock")


class InventoryCategoryViewSet(InventoryReadManageMixin, viewsets.ModelViewSet):
    serializer_class = InventoryCategorySerializer
    search_fields = ["name", "slug", "description"]
    filterset_fields = ["is_active", "parent"]
    ordering_fields = ["name", "created_at"]

    def get_queryset(self):
        return InventoryCategory.objects.select_related("parent").order_by("name")

    def perform_create(self, serializer):
        category = serializer.save()
        audit_log(user=self.request.user, action="inventory.api_category_create", target=category, after={"name": category.name, "slug": category.slug})


class InventoryItemViewSet(InventoryReadManageMixin, viewsets.ModelViewSet):
    serializer_class = InventoryItemSerializer
    search_fields = ["sku", "name", "description", "category__name"]
    filterset_fields = ["status", "item_type", "category", "track_stock", "is_public"]
    ordering_fields = ["name", "sku", "price", "created_at"]

    def get_queryset(self):
        return inventory_item_queryset(user=self.request.user, query="")

    def perform_create(self, serializer):
        item = serializer.save(created_by=self.request.user)
        audit_log(user=self.request.user, action="inventory.api_item_create", target=item, after={"sku": item.sku, "name": item.name, "status": item.status})

    def perform_update(self, serializer):
        before = {"sku": serializer.instance.sku, "name": serializer.instance.name, "status": serializer.instance.status}
        item = serializer.save()
        audit_log(user=self.request.user, action="inventory.api_item_update", target=item, before=before, after={"sku": item.sku, "name": item.name, "status": item.status})


class BranchStockViewSet(InventoryReadManageMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = BranchStockSerializer
    search_fields = ["item__sku", "item__name", "branch__name", "location_code"]
    filterset_fields = ["item", "branch"]
    ordering_fields = ["quantity", "minimum_stock", "updated_at"]

    def get_queryset(self):
        return stock_by_branch_queryset(user=self.request.user)

    @action(detail=False, methods=["get"], url_path="low-stock")
    def low_stock(self, request):
        queryset = low_stock_queryset(request.user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(self.get_serializer(queryset, many=True).data)


class StockMovementViewSet(InventoryReadManageMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = StockMovementSerializer
    search_fields = ["item__sku", "item__name", "reference", "reason", "branch__name"]
    filterset_fields = ["item", "branch", "destination_branch", "movement_type", "status"]
    ordering_fields = ["confirmed_at", "created_at", "quantity"]

    def get_queryset(self):
        return stock_movements_queryset(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            if data["movement_type"] == StockMovement.MovementType.TRANSFER:
                movement = transfer_stock(
                    actor=request.user,
                    item=data["item"],
                    origin_branch=data["branch"],
                    destination_branch=data.get("destination_branch"),
                    quantity=data["quantity"],
                    reference=data.get("reference", ""),
                    reason=data.get("reason", ""),
                )
            else:
                movement = record_stock_movement(
                    actor=request.user,
                    item=data["item"],
                    branch=data["branch"],
                    movement_type=data["movement_type"],
                    quantity=data["quantity"],
                    unit_cost=data.get("unit_cost"),
                    reference=data.get("reference", ""),
                    reason=data.get("reason", ""),
                )
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.messages) from exc
        return Response(self.get_serializer(movement).data, status=201)
