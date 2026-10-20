"""ES: Este módulo declara el enrutamiento URL para el dominio de sucursales.

EN: This module declares URL routing for the branches domain.

Contexto existente / Existing context:
URL routing for the branches domain.
"""

from django.urls import path
from apps.branches.views import BranchCreateView, BranchDetailView, BranchListView, BranchUpdateView

app_name = "branches"

urlpatterns = [
    path("", BranchListView.as_view(), name="list"),
    path("new/", BranchCreateView.as_view(), name="create"),
    path("<int:pk>/", BranchDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", BranchUpdateView.as_view(), name="update"),
]
