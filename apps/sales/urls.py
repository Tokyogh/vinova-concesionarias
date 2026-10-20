"""ES: Este módulo declara el enrutamiento URL para el dominio de ventas.

EN: This module declares URL routing for the sales domain.

Contexto existente / Existing context:
URL routing for the sales domain.
"""

from django.urls import path

from apps.sales.views import (
    InternalSaleActionView,
    InternalSaleCreateView,
    InternalSaleDetailView,
    InternalSaleLineCreateView,
    InternalSaleListView,
    InternalSalePaymentCreateView,
    InternalSalePaymentVoidView,
    InternalSaleUpdateView,
    InternalSalesAttentionView,
)

app_name = "sales_internal"

urlpatterns = [
    path("", InternalSaleListView.as_view(), name="list"),
    path("new/", InternalSaleCreateView.as_view(), name="create"),
    path("attention/", InternalSalesAttentionView.as_view(), name="attention"),
    path("<int:pk>/", InternalSaleDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", InternalSaleUpdateView.as_view(), name="update"),
    path("<int:pk>/lines/new/", InternalSaleLineCreateView.as_view(), name="line_create"),
    path("<int:pk>/payments/new/", InternalSalePaymentCreateView.as_view(), name="payment_create"),
    path(
        "<int:pk>/payments/<int:payment_pk>/void/",
        InternalSalePaymentVoidView.as_view(),
        name="payment_void",
    ),
    path("<int:pk>/action/<str:action>/", InternalSaleActionView.as_view(), name="action"),
]
