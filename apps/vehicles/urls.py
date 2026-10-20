"""ES: Este módulo declara el enrutamiento URL para el dominio de vehículos.

EN: This module declares URL routing for the vehicles domain.

Contexto existente / Existing context:
URL routing for the vehicles domain.
"""

from django.urls import path

from apps.vehicles.views import VehicleCatalogView, VehicleDetailModalView, VehiclePublicDetailView, VehicleRedeemCodeView

app_name = "vehicles"

urlpatterns = [
    path("", VehicleCatalogView.as_view(), name="catalog"),
    path("canjear/", VehicleRedeemCodeView.as_view(), name="redeem"),
    path("<slug:slug>/", VehiclePublicDetailView.as_view(), name="detail"),
    path("<int:pk>/modal/", VehicleDetailModalView.as_view(), name="detail_modal"),
]
