"""ES: Este módulo implementa el componente schema urls para el dominio de API e integraciones.

EN: This module implements the schema urls component for the api domain.

Contexto existente / Existing context:
Schema urls support for the api domain.
"""

from django.urls import include, path

urlpatterns = [
    path("api/v1/", include("apps.api.v1_urls")),
]
