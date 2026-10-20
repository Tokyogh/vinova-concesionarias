"""ES: Este módulo declara el enrutamiento URL para el dominio de empresa.

EN: This module declares URL routing for the companies domain.

Contexto existente / Existing context:
URL routing for the companies domain.
"""

from django.urls import path
from apps.companies.views import CompanyCreateView, CompanyDetailView, CompanyListView, CompanyUpdateView

app_name = "companies"

urlpatterns = [
    path("", CompanyListView.as_view(), name="list"),
    path("new/", CompanyCreateView.as_view(), name="create"),
    path("<int:pk>/", CompanyDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", CompanyUpdateView.as_view(), name="update"),
]
