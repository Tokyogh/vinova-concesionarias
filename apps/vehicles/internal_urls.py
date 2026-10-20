"""ES: Este módulo implementa el componente internal urls para el dominio de vehículos.

EN: This module implements the internal urls component for the vehicles domain.

Contexto existente / Existing context:
Internal urls support for the vehicles domain.
"""

from django.urls import path

from apps.vehicles.views import (
    InternalCustomerVehicleUnlinkView,
    InternalVehicleCreateView,
    InternalVehicleDetailView,
    InternalVehicleLinkCodeGenerateView,
    InternalVehicleLinkCodeRevokeView,
    InternalVehicleHighlightDeleteView,
    InternalVehicleHighlightFormView,
    InternalVehicleListView,
    InternalVehicleMediaUploadView,
    InternalVehicleMediaDeleteView,
    InternalVehicleMediaEditView,
    InternalVehicleSpecificationDeleteView,
    InternalVehicleSpecificationFormView,
    InternalVehicleStatusView,
    InternalVehicleTransferView,
    InternalVehicleUpdateView,
    VehicleBrandCreateView,
    VehicleCatalogDataView,
    VehicleModelCreateView,
)

app_name = "vehicles_internal"

urlpatterns = [
    path("", InternalVehicleListView.as_view(), name="list"),
    path("new/", InternalVehicleCreateView.as_view(), name="create"),
    path("catalog-data/", VehicleCatalogDataView.as_view(), name="catalog_data"),
    path("catalog-data/brands/new/", VehicleBrandCreateView.as_view(), name="brand_create"),
    path("catalog-data/models/new/", VehicleModelCreateView.as_view(), name="model_create"),
    path("<int:pk>/", InternalVehicleDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", InternalVehicleUpdateView.as_view(), name="update"),
    path("<int:pk>/media/upload/", InternalVehicleMediaUploadView.as_view(), name="media_upload"),
    path("<int:pk>/media/<int:item_pk>/edit/", InternalVehicleMediaEditView.as_view(), name="media_edit"),
    path("<int:pk>/media/<int:item_pk>/delete/", InternalVehicleMediaDeleteView.as_view(), name="media_delete"),
    path("<int:pk>/highlights/new/", InternalVehicleHighlightFormView.as_view(), name="highlight_create"),
    path("<int:pk>/highlights/<int:item_pk>/edit/", InternalVehicleHighlightFormView.as_view(), name="highlight_edit"),
    path("<int:pk>/highlights/<int:item_pk>/delete/", InternalVehicleHighlightDeleteView.as_view(), name="highlight_delete"),
    path("<int:pk>/specifications/new/", InternalVehicleSpecificationFormView.as_view(), name="specification_create"),
    path("<int:pk>/specifications/<int:item_pk>/edit/", InternalVehicleSpecificationFormView.as_view(), name="specification_edit"),
    path("<int:pk>/specifications/<int:item_pk>/delete/", InternalVehicleSpecificationDeleteView.as_view(), name="specification_delete"),
    path("<int:pk>/link-code/generate/", InternalVehicleLinkCodeGenerateView.as_view(), name="link_code_generate"),
    path("<int:pk>/link-code/<int:code_pk>/revoke/", InternalVehicleLinkCodeRevokeView.as_view(), name="link_code_revoke"),
    path("<int:pk>/garage/<int:link_pk>/unlink/", InternalCustomerVehicleUnlinkView.as_view(), name="garage_unlink"),
    path("<int:pk>/garage/<int:link_pk>/transfer/", InternalVehicleTransferView.as_view(), name="garage_transfer"),
    path("<int:pk>/<str:action>/", InternalVehicleStatusView.as_view(), name="status_action"),
]
