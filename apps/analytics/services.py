"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de analítica.

EN: This module implements business services and transactional effects for the analytics domain.

Contexto existente / Existing context:
Transactional business services for the analytics domain.
"""

from __future__ import annotations

import hashlib

from django.conf import settings

from apps.analytics.models import VehicleInteraction
from apps.privacy.cookies import cookie_category_allowed


def _hash(value: str) -> str:
    if not value:
        return ""
    return hashlib.sha256(f"{settings.SECRET_KEY}:{value}".encode("utf-8")).hexdigest()


def request_identity(request) -> dict[str, str]:
    if not request.session.session_key:
        request.session.create()
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "") if getattr(settings, "VINOVA_TRUST_PROXY_HEADERS", False) else ""
    ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR", "")
    return {
        "session_hash": _hash(request.session.session_key or ""),
        "ip_hash": _hash(ip),
        "source_url": request.build_absolute_uri()[:500],
        "referrer": request.META.get("HTTP_REFERER", "")[:500],
    }


def record_vehicle_interaction(*, request, event_type: str, vehicle=None, lead=None, city: str = "", province: str = "", metadata=None):
    """ES: Registra analítica solo tras aceptación. EN: Records analytics only after opt-in."""

    if not cookie_category_allowed(request, "analytics"):
        return None
    identity = request_identity(request)
    return VehicleInteraction.objects.create(
        event_type=event_type,
        vehicle=vehicle,
        lead=lead,
        user=request.user if getattr(request.user, "is_authenticated", False) else None,
        branch=getattr(vehicle, "branch", None) or getattr(lead, "branch", None),
        city=(city or getattr(lead, "city", ""))[:90],
        province=(province or getattr(lead, "province", ""))[:90],
        utm_source=request.GET.get("utm_source", request.POST.get("utm_source", ""))[:120],
        utm_medium=request.GET.get("utm_medium", request.POST.get("utm_medium", ""))[:120],
        utm_campaign=request.GET.get("utm_campaign", request.POST.get("utm_campaign", ""))[:160],
        metadata=metadata or {},
        **identity,
    )
