"""ES: Este módulo implementa el componente logging para el dominio de infraestructura compartida.

EN: This module implements the logging component for the common domain.

Contexto existente / Existing context:
Logging support for the common domain.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime


_AUTHORIZATION_PATTERN = re.compile(
    r"(?i)(authorization[\"']?\s*[=:]\s*[\"']?(?:bearer|basic)\s+)([^\"'\s,;}\]]+)"
)
_SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?i)([\"']?(?:password|passwd|secret|token|authorization|cookie|totp|api[_-]?key)[\"']?\s*[=:]\s*)"
    r"([\"']?)([^\"'\s,;}\]]+)([\"']?)"
)
_CREDENTIAL_URL_PATTERN = re.compile(r"(?i)(redis|postgres(?:ql)?|mysql)://([^:@/\s]+):([^@/\s]+)@")


def redact_sensitive(value: object) -> str:
    text = str(value)
    text = _AUTHORIZATION_PATTERN.sub(r"\1***", text)
    text = _SENSITIVE_VALUE_PATTERN.sub(r"\1\2***\4", text)
    text = _CREDENTIAL_URL_PATTERN.sub(r"\1://\2:***@", text)
    return text


class SensitiveDataFilter(logging.Filter):
    """Evita que secretos comunes terminen en stdout o en el colector de logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            rendered = record.getMessage()
        except Exception:  # noqa: BLE001 - logging must never break the application
            rendered = str(record.msg)
        record.msg = redact_sensitive(rendered)
        record.args = ()
        return True


class JsonFormatter(logging.Formatter):
    """Formato JSON compacto para Docker, journald y plataformas de observabilidad."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_sensitive(record.getMessage()),
        }
        request_id = getattr(record, "request_id", "")
        if request_id:
            payload["request_id"] = request_id
        if record.exc_info:
            payload["exception"] = redact_sensitive(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False)
