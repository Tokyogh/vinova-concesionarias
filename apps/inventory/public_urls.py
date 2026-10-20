"""ES: Este módulo implementa el componente public urls para el dominio de inventario.

EN: This module implements the public urls component for the inventory domain.

Contexto existente / Existing context:
Rutas del catálogo público de repuestos.

Routes for the public spare-parts catalog.
"""

from django.urls import path

from apps.inventory.views import PublicInventoryCatalogView

app_name = "parts"

urlpatterns = [path("", PublicInventoryCatalogView.as_view(), name="catalog")]
