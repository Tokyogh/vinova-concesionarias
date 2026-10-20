"""ES: Este módulo declara el enrutamiento URL para el dominio de configuración SRI heredada.

EN: This module declares URL routing for the sri integration domain.

Contexto existente / Existing context:
URL routing for the sri integration domain.
"""

from django.urls import path

from apps.sri_integration.views import (
    SriConfigurationUpdateView,
    SriEstablishmentCreateView,
    SriEstablishmentListView,
    SriEstablishmentUpdateView,
    SriSequenceCreateView,
    SriSequenceListView,
    SriSequenceUpdateView,
)

app_name = "sri_integration"

urlpatterns = [
    path("", SriConfigurationUpdateView.as_view(), name="configuration"),
    path("establishments/", SriEstablishmentListView.as_view(), name="establishments"),
    path("establishments/new/", SriEstablishmentCreateView.as_view(), name="establishment_create"),
    path("establishments/<int:pk>/", SriEstablishmentUpdateView.as_view(), name="establishment_update"),
    path("sequences/", SriSequenceListView.as_view(), name="sequences"),
    path("sequences/new/", SriSequenceCreateView.as_view(), name="sequence_create"),
    path("sequences/<int:pk>/", SriSequenceUpdateView.as_view(), name="sequence_update"),
]
