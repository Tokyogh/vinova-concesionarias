"""ES: Este módulo declara el enrutamiento URL para el dominio de calidad.

EN: This module declares URL routing for the quality domain.

Contexto existente / Existing context:
URL routing for the quality domain.
"""

from django.urls import path

from apps.quality.api.views import QualityRunCreateAPIView, QualityRunDetailAPIView, QualityRunListAPIView

app_name = "quality-api"

urlpatterns = [
    path("runs/", QualityRunListAPIView.as_view(), name="run_list"),
    path("runs/execute/", QualityRunCreateAPIView.as_view(), name="run_create"),
    path("runs/<uuid:public_id>/", QualityRunDetailAPIView.as_view(), name="run_detail"),
]
