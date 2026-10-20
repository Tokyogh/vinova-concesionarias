"""ES: Este módulo declara el enrutamiento URL para el dominio de inventario.

EN: This module declares URL routing for the inventory domain.

Contexto existente / Existing context:
URL routing for the inventory domain.
"""

from django.urls import path

from apps.inventory.views import (
    InternalInventoryCreateView,
    InternalInventoryDetailView,
    InternalInventoryListView,
    InternalInventoryStatusView,
    InternalInventoryUpdateView,
    InternalBranchStockSettingsView,
    InternalItemStockMovementCreateView,
    InternalLowStockView,
    InternalStockMovementCreateView,
    InternalStockMovementListView,
    InternalStockTransferCreateView,
    InventoryCatalogDataView,
    InventoryCategoryCreateView,
)

app_name = "inventory_internal"

urlpatterns = [
    path("", InternalInventoryListView.as_view(), name="list"),
    path("new/", InternalInventoryCreateView.as_view(), name="create"),
    path("catalog-data/", InventoryCatalogDataView.as_view(), name="catalog_data"),
    path("catalog-data/categories/new/", InventoryCategoryCreateView.as_view(), name="category_create"),
    path("low-stock/", InternalLowStockView.as_view(), name="low_stock"),
    path("movements/", InternalStockMovementListView.as_view(), name="movement_list"),
    path("movements/new/", InternalStockMovementCreateView.as_view(), name="movement_create"),
    path("transfers/new/", InternalStockTransferCreateView.as_view(), name="transfer_create"),
    path("<int:pk>/", InternalInventoryDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", InternalInventoryUpdateView.as_view(), name="update"),
    path("<int:pk>/stock/new/", InternalItemStockMovementCreateView.as_view(), name="stock_movement_create"),
    path("<int:pk>/stock/<int:stock_pk>/settings/", InternalBranchStockSettingsView.as_view(), name="stock_settings"),
    path("<int:pk>/<str:action>/", InternalInventoryStatusView.as_view(), name="status_action"),
]
