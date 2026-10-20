"""ES: Este módulo implementa el componente rate limit para el dominio de infraestructura compartida.

EN: This module implements the rate limit component for the common domain.

Contexto existente / Existing context:
Rate limiting helpers for the common domain.
"""

import hashlib
import logging

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse


logger = logging.getLogger(__name__)


def _client_ip(request):
    if getattr(settings, "VINOVA_TRUST_PROXY_HEADERS", False):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",", 1)[0].strip()
    return request.META.get("REMOTE_ADDR", "") or "unknown"


def public_rate_limit_exceeded(request, *, scope):
    limit = max(1, int(getattr(settings, "VINOVA_PUBLIC_FORM_MAX_SUBMISSIONS", 8)))
    window = max(60, int(getattr(settings, "VINOVA_PUBLIC_FORM_WINDOW_SECONDS", 3600)))
    identity = hashlib.sha256(f"{settings.SECRET_KEY}:{scope}:{_client_ip(request)}".encode()).hexdigest()
    key = f"vinova:public-form:{scope}:{identity}"
    try:
        if cache.add(key, 1, timeout=window):
            return False
        return int(cache.incr(key)) > limit
    except Exception:
        logger.exception("Public form rate-limit cache unavailable", extra={"scope": scope})
        return False


def public_rate_limited_response():
    response = HttpResponse("Demasiadas solicitudes. Intenta nuevamente más tarde.", status=429)
    response["Retry-After"] = str(max(60, int(getattr(settings, "VINOVA_PUBLIC_FORM_WINDOW_SECONDS", 3600))))
    return response
