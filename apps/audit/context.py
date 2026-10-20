"""ES: Este módulo implementa el componente context para el dominio de auditoría.

EN: This module implements the context component for the audit domain.

Contexto existente / Existing context:
Context support for the audit domain.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

_audit_context: ContextVar[dict[str, Any]] = ContextVar("vinova_audit_context", default={})


def set_audit_context(data: dict[str, Any]):
    return _audit_context.set(data)


def reset_audit_context(token) -> None:
    _audit_context.reset(token)


def get_audit_context() -> dict[str, Any]:
    return dict(_audit_context.get() or {})
