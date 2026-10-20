"""ES: Este módulo declara el enrutamiento URL para el dominio de clientes.

EN: This module declares URL routing for the customers domain.

Contexto existente / Existing context:
URL routing for the customers domain.
"""

from django.urls import path

from apps.customers.views import (
    InternalCustomerAddInterestView,
    InternalCustomerAddNoteView,
    InternalCustomerCreateView,
    InternalCustomerDetailView,
    InternalCustomerInviteAccountView,
    InternalCustomerLinkAccountView,
    InternalCustomerListView,
    InternalCustomerStatusView,
    InternalCustomerUpdateView,
)

app_name = "customers_internal"

urlpatterns = [
    path("", InternalCustomerListView.as_view(), name="list"),
    path("new/", InternalCustomerCreateView.as_view(), name="create"),
    path("<int:pk>/", InternalCustomerDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", InternalCustomerUpdateView.as_view(), name="update"),
    path("<int:pk>/status/<str:action>/", InternalCustomerStatusView.as_view(), name="status_action"),
    path("<int:pk>/notes/new/", InternalCustomerAddNoteView.as_view(), name="add_note"),
    path("<int:pk>/interests/new/", InternalCustomerAddInterestView.as_view(), name="add_interest"),
    path("<int:pk>/account/link/", InternalCustomerLinkAccountView.as_view(), name="link_account"),
    path("<int:pk>/account/invite/", InternalCustomerInviteAccountView.as_view(), name="invite_account"),
]
