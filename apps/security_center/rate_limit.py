"""ES: Este módulo implementa el componente rate limit para el dominio de seguridad.

EN: This module implements the rate limit component for the security center domain.

Contexto existente / Existing context:
Rate limiting helpers for the security center domain.
"""

from __future__ import annotations

import hashlib
import logging

from django.conf import settings
from django.core.cache import cache

from apps.security_center.models import SecurityPolicy

logger = logging.getLogger(__name__)


def _hash(value: str) -> str:
    return hashlib.sha256(f"{settings.SECRET_KEY}:{value}".encode("utf-8")).hexdigest()


def client_ip(request) -> str:
    if request is None:
        return "unknown"
    if getattr(settings, "VINOVA_TRUST_PROXY_HEADERS", False):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",", 1)[0].strip()
    return request.META.get("REMOTE_ADDR", "") or "unknown"


def _keys(request, login: str):
    ip = client_ip(request)
    return [f"vinova:login:ip:{_hash(ip)}", f"vinova:login:pair:{_hash(ip + '|' + login.lower())}"]


def is_blocked(request, login: str) -> bool:
    policy = SecurityPolicy.current()
    try:
        return any(int(cache.get(key, 0) or 0) >= policy.login_attempts_per_ip for key in _keys(request, login))
    except Exception:  # noqa: BLE001 - preserve login availability while surfacing cache outages
        logger.exception("Login rate-limit cache unavailable")
        return False


def register_failure(request, login: str) -> None:
    policy = SecurityPolicy.current()
    timeout = max(60, policy.login_window_minutes * 60)
    for key in _keys(request, login):
        try:
            try:
                cache.incr(key)
            except ValueError:
                cache.set(key, 1, timeout=timeout)
            else:
                cache.touch(key, timeout=timeout)
        except Exception:  # noqa: BLE001 - preserve login availability while surfacing cache outages
            logger.exception("Login rate-limit cache unavailable")


def clear_failures(request, login: str) -> None:
    try:
        cache.delete_many(_keys(request, login))
    except Exception:  # noqa: BLE001 - a cache outage must not invalidate correct credentials
        logger.exception("Login rate-limit cache unavailable")


def _two_factor_keys(request, user) -> list[str]:
    ip = client_ip(request)
    return [
        f"vinova:2fa:ip:{_hash(ip)}",
        f"vinova:2fa:pair:{_hash(f'{ip}|{user.pk}')}",
    ]


def is_two_factor_blocked(request, user) -> bool:
    """ES: Limita fuerza bruta 2FA. EN: Limits authenticated 2FA brute force."""

    policy = SecurityPolicy.current()
    try:
        return any(int(cache.get(key, 0) or 0) >= policy.login_attempts_per_ip for key in _two_factor_keys(request, user))
    except Exception:  # noqa: BLE001 - preserve authentication availability while surfacing cache outages
        logger.exception("Two-factor rate-limit cache unavailable")
        return False


def register_two_factor_failure(request, user) -> None:
    policy = SecurityPolicy.current()
    timeout = max(60, policy.login_window_minutes * 60)
    for key in _two_factor_keys(request, user):
        try:
            if cache.add(key, 1, timeout=timeout):
                continue
            cache.incr(key)
            cache.touch(key, timeout=timeout)
        except Exception:  # noqa: BLE001 - an unavailable cache must not crash authentication
            logger.exception("Two-factor rate-limit cache unavailable")


def clear_two_factor_failures(request, user) -> None:
    try:
        cache.delete_many(_two_factor_keys(request, user))
    except Exception:  # noqa: BLE001 - a cache outage must not invalidate a correct second factor
        logger.exception("Two-factor rate-limit cache unavailable")
