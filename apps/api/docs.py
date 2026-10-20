"""ES: Este módulo implementa el componente docs para el dominio de API e integraciones.

EN: This module implements the docs component for the api domain.

Contexto existente / Existing context:
Docs support for the api domain.
"""

from django.conf import settings
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny, IsAdminUser


def _permission_classes():
    return [AllowAny] if settings.VINOVA_API_DOCS_PUBLIC else [IsAdminUser]


class VinovaSpectacularAPIView(SpectacularAPIView):
    permission_classes = _permission_classes()


class VinovaSpectacularSwaggerView(SpectacularSwaggerView):
    permission_classes = _permission_classes()
