"""ES: Este módulo implementa el componente throttling para el dominio de API e integraciones.

EN: This module implements the throttling component for the api domain.

Contexto existente / Existing context:
Request throttling controls for the api domain.
"""

from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


class APIClientRateThrottle(SimpleRateThrottle):
    scope = "api_client"

    def allow_request(self, request, view):
        client = getattr(request, "api_client", None)
        if not client:
            return True
        self.rate = client.rate_limit or getattr(settings, "VINOVA_API_CLIENT_DEFAULT_RATE", "600/hour")
        self.num_requests, self.duration = self.parse_rate(self.rate)
        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        client = getattr(request, "api_client", None)
        if not client:
            return None
        return self.cache_format % {"scope": self.scope, "ident": client.public_id.hex}
