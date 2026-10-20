"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for public in the deployment_smoke domain.
"""

from __future__ import annotations

from tests.deployment_smoke.helpers.http import absolute, request
from tests.deployment_smoke.helpers.runtime import run_check

__test__ = False


def run(state, session=None):  # noqa: ANN001
    config = state.config
    run_check(
        state,
        code="public.home_http",
        scenario="public",
        title="Portada pública por HTTP",
        callback=lambda: _home(config.base_url, config.timeout_seconds, config.verify_tls),
        retryable=True,
    )
    if session is None:
        return
    run_check(
        state,
        code="public.home_browser",
        scenario="public",
        title="Portada, main, título y recursos públicos",
        callback=lambda: _browser_home(session),
        retryable=True,
    )


def _home(base_url: str, timeout: int, verify_tls: bool) -> dict:
    response = request(absolute(base_url, "/"), timeout=timeout, verify_tls=verify_tls)
    if response.status >= 400:
        raise AssertionError(f"La portada respondió HTTP {response.status}.")
    lower = response.text.lower()
    if "<html" not in lower or "<main" not in lower:
        raise AssertionError("La portada no contiene la estructura HTML esperada.")
    return {"status_code": response.status, "elapsed_seconds": round(response.elapsed_seconds, 3)}


def _browser_home(session) -> dict:  # noqa: ANN001
    page = session.goto("/")
    if not page.title().strip():
        raise AssertionError("La portada no tiene título.")
    if page.locator("main").count() == 0:
        raise AssertionError("La portada no contiene <main>.")
    broken: list[str] = []
    urls = page.locator("link[rel='stylesheet'], script[src], img[src], link[rel~='icon']").evaluate_all(
        "els => els.map(el => el.href || el.src).filter(Boolean)"
    )
    for url in urls[:80]:
        response = page.request.get(url, timeout=session.timeout_ms)
        if response.status >= 400:
            broken.append(f"{response.status} {url}")
    if broken:
        raise AssertionError("Recursos públicos rotos: " + "; ".join(broken[:8]))
    shot = session.screenshot("public-home")
    return {"title": page.title(), "assets_checked": len(urls), "evidence": [shot]}
