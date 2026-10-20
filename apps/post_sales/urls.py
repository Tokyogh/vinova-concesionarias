"""ES: Este módulo declara el enrutamiento URL para el dominio de postventa.

EN: This module declares URL routing for the post sales domain.

Contexto existente / Existing context:
URL routing for the post sales domain.
"""

from django.urls import path

from apps.post_sales.views import (
    ServiceOrderCreateView,
    ServiceOrderDetailView,
    ServiceOrderLineCreateView,
    ServiceOrderListView,
    ServiceOrderOperationalUpdateView,
    ServiceOrderStatusView,
)


app_name = "post_sales"

urlpatterns = [
    path("", ServiceOrderListView.as_view(), name="list"),
    path("new/", ServiceOrderCreateView.as_view(), name="create"),
    path("<int:pk>/", ServiceOrderDetailView.as_view(), name="detail"),
    path("<int:pk>/status/", ServiceOrderStatusView.as_view(), name="status"),
    path("<int:pk>/lines/new/", ServiceOrderLineCreateView.as_view(), name="line_create"),
    path("<int:pk>/operational/", ServiceOrderOperationalUpdateView.as_view(), name="operational_update"),
]
