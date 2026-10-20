"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for security in the deployment_smoke helpers domain.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from urllib.parse import urlparse

SENSITIVE_PATTERN = re.compile(
    r"(?i)(password|secret|token|authorization|cookie|set-cookie|private[_-]?key|api[_-]?key)(\s*[:=]\s*)([^\s,;]+)"
)


def redact(text: str, secrets: Iterable[str] = ()) -> str:
    cleaned = str(text)
    for secret in sorted({item for item in secrets if item and len(item) >= 4}, key=len, reverse=True):
        cleaned = cleaned.replace(secret, "[REDACTED]")
    return SENSITIVE_PATTERN.sub(r"\1\2[REDACTED]", cleaned)


def validate_target_url(url: str, *, allow_http_local: bool = False) -> str:
    parsed = urlparse(url.strip())
    if parsed.username or parsed.password:
        raise ValueError("La URL objetivo no puede contener credenciales.")
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("La URL objetivo debe ser absoluta y usar HTTP o HTTPS.")
    local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and not (allow_http_local and local):
        raise ValueError("HTTPS es obligatorio. HTTP solo se permite para pruebas locales explícitas.")
    return url.rstrip("/")


def normalized_headers(headers: object) -> dict[str, str]:
    if hasattr(headers, "items"):
        return {str(key).lower(): str(value) for key, value in headers.items()}
    return {}
