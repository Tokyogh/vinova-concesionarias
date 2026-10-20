"""ES: Este módulo registra modelos en la administración de Django para el dominio de inventario.

EN: This module registers models in Django admin for the inventory domain.

Contexto existente / Existing context:
Django admin registrations for the inventory domain.
"""

from django.contrib import admin

from apps.inventory.models import BranchStock, InventoryCategory, InventoryItem, StockMovement


@admin.register(InventoryCategory)
class InventoryCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "is_active", "created_at")
    search_fields = ("name", "slug", "description")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "item_type", "category", "status", "price", "track_stock", "is_public")
    search_fields = ("sku", "name", "description")
    list_filter = ("status", "item_type", "category", "track_stock", "is_public")
    autocomplete_fields = ("category", "created_by")


@admin.register(BranchStock)
class BranchStockAdmin(admin.ModelAdmin):
    list_display = ("item", "branch", "quantity", "reserved_quantity", "minimum_stock", "location_code", "last_movement_at")
    search_fields = ("item__sku", "item__name", "branch__name", "location_code")
    list_filter = ("branch",)
    autocomplete_fields = ("item", "branch")
    readonly_fields = (
        "item",
        "branch",
        "quantity",
        "reserved_quantity",
        "minimum_stock",
        "location_code",
        "last_movement_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("item", "branch", "destination_branch", "movement_type", "quantity", "status", "reference", "confirmed_at", "created_by")
    search_fields = ("item__sku", "item__name", "branch__name", "destination_branch__name", "reference", "reason")
    list_filter = ("movement_type", "status", "branch", "destination_branch")
    autocomplete_fields = ("item", "branch", "destination_branch", "created_by")
    readonly_fields = (
        "item",
        "branch",
        "destination_branch",
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
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
