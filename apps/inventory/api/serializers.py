"""ES: Este módulo serializa y valida contratos de API para el dominio de inventario.

EN: This module serializes and validates API contracts for the inventory domain.

Contexto existente / Existing context:
REST serializers and API validation for the inventory domain.
"""

from decimal import Decimal

from rest_framework import serializers

from apps.common.validators import validate_no_unsafe_control_characters, validate_nonnegative_decimal
from apps.inventory.models import BranchStock, InventoryCategory, InventoryItem, StockMovement


class InventoryCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryCategory
        fields = ["id", "name", "slug", "parent", "description", "is_active", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class InventoryItemSerializer(serializers.ModelSerializer):
    total_stock = serializers.SerializerMethodField()
    has_low_stock = serializers.SerializerMethodField()

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "category",
            "name",
            "sku",
            "item_type",
            "description",
            "unit",
            "price",
            "cost",
            "image",
            "status",
            "is_public",
            "track_stock",
            "total_stock",
            "has_low_stock",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]
        extra_kwargs = {
            "name": {"validators": [validate_no_unsafe_control_characters]},
            "description": {"validators": [validate_no_unsafe_control_characters]},
            "unit": {"validators": [validate_no_unsafe_control_characters]},
            "price": {"validators": [validate_nonnegative_decimal], "min_value": Decimal("0")},
            "cost": {"validators": [validate_nonnegative_decimal], "min_value": Decimal("0")},
        }

    def get_total_stock(self, obj: InventoryItem) -> Decimal:
        return getattr(obj, "total_stock_amount", None) or Decimal("0")

    def get_has_low_stock(self, obj: InventoryItem) -> bool:
        return bool(getattr(obj, "has_low_stock_scoped", False))


class BranchStockSerializer(serializers.ModelSerializer):
    item_sku = serializers.CharField(source="item.sku", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    available_quantity = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = BranchStock
        fields = [
            "id",
            "item",
            "item_sku",
            "item_name",
            "branch",
            "branch_name",
            "quantity",
            "reserved_quantity",
            "available_quantity",
            "minimum_stock",
            "is_low_stock",
            "location_code",
            "last_movement_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["quantity", "reserved_quantity", "last_movement_at", "created_at", "updated_at"]


class StockMovementSerializer(serializers.ModelSerializer):
    item_sku = serializers.CharField(source="item.sku", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    destination_branch_name = serializers.CharField(source="destination_branch.name", read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "item",
            "item_sku",
            "item_name",
            "branch",
            "branch_name",
            "destination_branch",
            "destination_branch_name",
            "movement_type",
            "status",
            "quantity",
            "previous_quantity",
            "new_quantity",
            "destination_previous_quantity",
            "destination_new_quantity",
            "unit_cost",
            "reference",
            "reason",
            "created_by",
            "confirmed_at",
            "created_at",
        ]
        read_only_fields = [
            "status",
            "previous_quantity",
            "new_quantity",
            "destination_previous_quantity",
            "destination_new_quantity",
            "created_by",
            "confirmed_at",
            "created_at",
        ]
