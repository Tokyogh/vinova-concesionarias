"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for health in the deployment_smoke domain.
"""

from __future__ import annotations

import json

from tests.deployment_smoke.helpers.http import absolute, request
from tests.deployment_smoke.helpers.runtime import run_check

__test__ = False


def run(state, session=None):  # noqa: ANN001
    config = state.config
    for path, expected, code, title in [
        ("/health/live/", "ok", "health.live", "Liveness"),
        ("/health/ready/", "ready", "health.ready", "Readiness"),
    ]:
        run_check(
            state,
            code=code,
            scenario="health",
            title=title,
            callback=lambda path=path, expected=expected: _health(config.base_url, path, expected, config.timeout_seconds, config.verify_tls),
            retryable=True,
        )
    run_check(
        state,
        code="health.dependencies_protected",
        scenario="health",
        title="Dependencias protegidas sin autenticación",
        callback=lambda: _protected(config.base_url, config.timeout_seconds, config.verify_tls),
    )
    if session is not None and config.username:
        run_check(
            state,
            code="health.dependencies_authenticated",
            scenario="health",
            title="Estado autenticado de PostgreSQL, Redis y almacenamiento",
            callback=lambda: _authenticated(session),
            required=False,
        )


def _health(base_url: str, path: str, expected: str, timeout: int, verify_tls: bool) -> dict:
    response = request(absolute(base_url, path), timeout=timeout, verify_tls=verify_tls)
    if response.status != 200:
        raise AssertionError(f"{path} respondió HTTP {response.status}.")
    payload = json.loads(response.text)
    if payload.get("status") != expected:
        raise AssertionError(f"{path} devolvió estado {payload.get('status')!r}.")
    return {"payload": payload, "elapsed_seconds": round(response.elapsed_seconds, 3)}


def _protected(base_url: str, timeout: int, verify_tls: bool) -> dict:
    response = request(absolute(base_url, "/health/dependencies/"), timeout=timeout, follow_redirects=False, verify_tls=verify_tls)
    if response.status not in {302, 303, 401, 403}:
        raise AssertionError(f"El endpoint de dependencias quedó expuesto: HTTP {response.status}.")
    return {"status_code": response.status, "location": response.headers.get("location", "")}


def _authenticated(session) -> dict:  # noqa: ANN001
    page = session.goto("/health/dependencies/")
    if "/accounts/login/" in page.url:
        raise AssertionError("La sesión autenticada no pudo consultar dependencias.")
    text = page.locator("body").inner_text()
    payload = json.loads(text)
    if payload.get("status") != "ready":
        raise AssertionError(f"Dependencias no disponibles: {payload}")
    return {"checks": payload.get("checks", {})}
