"""ES: Este módulo procesa controles transversales del ciclo HTTP para el dominio de auditoría.

EN: This module processes cross-cutting HTTP lifecycle controls for the audit domain.

Contexto existente / Existing context:
Request and response middleware for the audit domain.
"""

from __future__ import annotations

import logging
import uuid

from django.conf import settings
from django.core.exceptions import PermissionDenied

from apps.audit.context import reset_audit_context, set_audit_context

logger = logging.getLogger(__name__)


class AuditRequestMiddleware:
    """ES: Agrupa el componente «audit request middleware» del dominio de auditoría y sus reglas relacionadas. Además, aplica autorización en backend, registra efectos auditables.

    EN: Groups the «audit request middleware» component and its related rules in the audit domain. It also enforces server-side authorization, records auditable effects.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _client_ip(request) -> str:
        if getattr(settings, "VINOVA_TRUST_PROXY_HEADERS", False):
            forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
            if forwarded:
                return forwarded.split(",", 1)[0].strip()
        return request.META.get("REMOTE_ADDR", "") or ""

    def __call__(self, request):
        """ES: Ejecuta la operación «call» dentro del dominio de auditoría. Además, aplica autorización en backend, registra efectos auditables.

        EN: Executes the «call» operation within the audit domain. It also enforces server-side authorization, records auditable effects.
        """

        request_id = uuid.uuid4()
        request.audit_request_id = request_id
        request.audit_ip = self._client_ip(request)
        request.audit_user_agent = request.META.get("HTTP_USER_AGENT", "")[:2000]
        token = set_audit_context(
            {
                "request_id": request_id,
                "ip_address": request.audit_ip,
                "user_agent": request.audit_user_agent,
                "http_method": request.method,
                "request_path": request.path,
                "branch": getattr(getattr(request, "user", None), "branch", None),
            }
        )
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = str(request_id)
            if request.path.startswith(("/dashboard/", "/api/")) and response.status_code in {403, 429}:
                from apps.audit.services import audit_log

                audit_log(
                    user=getattr(request, "user", None),
                    action="security.permission_denied",
                    after={"status_code": response.status_code},
                )
            elif request.path.startswith(("/dashboard/", "/api/")) and response.status_code >= 500:
                from apps.audit.services import audit_log

                audit_log(
                    user=getattr(request, "user", None),
                    action="security.server_error",
                    after={"status_code": response.status_code},
                )
            return response
        except PermissionDenied:
            if request.path.startswith(("/dashboard/", "/api/")):
                try:
                    from apps.audit.services import audit_log

                    audit_log(
                        user=getattr(request, "user", None),
                        action="security.permission_denied",
                        after={"status_code": 403},
                    )
                except Exception:  # noqa: BLE001 - never replace the original authorization response
                    logger.exception(
                        "No se pudo persistir el evento de auditoría para una autorización denegada."
                    )
            raise
        except Exception as exc:
            if request.path.startswith(("/dashboard/", "/api/")):
                try:
                    from apps.audit.services import audit_log

                    audit_log(
                        user=getattr(request, "user", None),
                        action="security.server_error",
                        after={"exception_type": type(exc).__name__},
                    )
                except Exception:  # noqa: BLE001 - never mask the original application exception
                    logger.exception(
                        "No se pudo persistir el evento de auditoría para un error de servidor."
                    )
            raise
        finally:
            reset_audit_context(token)
