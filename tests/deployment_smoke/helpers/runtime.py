"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for runtime in the deployment_smoke helpers domain.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from tests.deployment_smoke.helpers.models import CheckResult, RunState
from tests.deployment_smoke.helpers.security import redact


def run_check(
    state: RunState,
    *,
    code: str,
    scenario: str,
    title: str,
    callback: Callable[[], Any],
    required: bool = True,
    retries: int | None = None,
    retryable: bool = False,
) -> CheckResult:
    attempts = max(1, (retries if retries is not None else state.config.retries) + 1) if retryable else 1
    started = time.monotonic()
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            result = callback()
            details: dict[str, Any] = {}
            message = "Control aprobado."
            evidence: list[str] = []
            status = "passed"
            if isinstance(result, dict):
                status = str(result.pop("status", status))
                message = str(result.pop("message", message))
                evidence = list(result.pop("evidence", []))
                details = result
            return state.add(
                CheckResult(
                    code=code,
                    scenario=scenario,
                    title=title,
                    status=status,
                    message=message,
                    duration_seconds=round(time.monotonic() - started, 3),
                    required=required,
                    evidence=evidence,
                    details=details,
                )
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < attempts:
                time.sleep(min(2.0 * attempt, 5.0))
    secrets = [state.config.password]
    message = redact(f"{type(last_error).__name__}: {last_error}", secrets)
    return state.add(
        CheckResult(
            code=code,
            scenario=scenario,
            title=title,
            status="failed",
            message=message,
            duration_seconds=round(time.monotonic() - started, 3),
            required=required,
        )
    )


def skip_check(
    state: RunState,
    *,
    code: str,
    scenario: str,
    title: str,
    message: str,
    required: bool,
) -> CheckResult:
    return state.add(
        CheckResult(
            code=code,
            scenario=scenario,
            title=title,
            status="skipped",
            message=message,
            required=required,
        )
    )
