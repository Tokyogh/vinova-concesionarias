"""ES: Este módulo implementa el componente public urls para el dominio de sucursales.

EN: This module implements the public urls component for the branches domain.

Contexto existente / Existing context:
Public urls support for the branches domain.
"""

from django.urls import path

from apps.branches.views import PublicInstitutionListView

app_name = "institutions"

urlpatterns = [
    path("", PublicInstitutionListView.as_view(), name="list"),
]
