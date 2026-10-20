"""ES: Este módulo procesa controles transversales del ciclo HTTP para el dominio de API e integraciones.

EN: This module processes cross-cutting HTTP lifecycle controls for the api domain.

Contexto existente / Existing context:
Request and response middleware for the api domain.
"""

from __future__ import annotations

import logging
import time

from apps.api.models import IntegrationLog
from apps.api.services import log_integration

logger = logging.getLogger(__name__)


class APIIntegrationLogMiddleware:
    """Record API-client calls without persisting request or response bodies."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.monotonic()
        response = self.get_response(request)
        client = getattr(request, "_vinova_api_client", None)
        if (
            not client
            or not request.path.startswith("/api/v1/")
            or getattr(request, "_vinova_skip_generic_integration_log", False)
        ):
            return response

        if response.status_code < 400:
            result = IntegrationLog.Status.SUCCESS
        elif response.status_code in {401, 403, 429}:
            result = IntegrationLog.Status.DENIED
        else:
            result = IntegrationLog.Status.FAILED
        try:
            log_integration(
                direction=IntegrationLog.Direction.INBOUND,
                category="api",
                action=f"api.{request.method.lower()}",
                status=result,
                client=client,
                user=getattr(request, "user", None),
                branch=client.branch,
                request_id=getattr(request, "audit_request_id", None),
                endpoint=request.path,
                http_method=request.method,
                http_status=response.status_code,
                duration_ms=int((time.monotonic() - started) * 1000),
                metadata={"api_version": "v1"},
            )
        except Exception:  # noqa: BLE001 - observability must not break the API response
            logger.exception("No fue posible registrar la llamada del cliente API")
        return response
