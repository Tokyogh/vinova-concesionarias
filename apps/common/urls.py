"""ES: Este módulo declara el enrutamiento URL para el dominio de infraestructura compartida.

EN: This module declares URL routing for the common domain.

Contexto existente / Existing context:
URL routing for the common domain.
"""

from django.urls import path

from apps.common.lookups import InternalLookupView

app_name = "common"

urlpatterns = [
    path("lookups/<slug:resource>/", InternalLookupView.as_view(), name="lookup"),
]
