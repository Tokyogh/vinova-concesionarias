"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for assets in the deployment_smoke domain.
"""

from __future__ import annotations

from tests.deployment_smoke.helpers.runtime import run_check

__test__ = False


def run(state, session=None):  # noqa: ANN001
    if session is None:
        return
    run_check(
        state,
        code="assets.authenticated_pages",
        scenario="assets",
        title="CSS, JavaScript e imágenes del panel",
        callback=lambda: _assets(session),
        retryable=True,
    )


def _assets(session) -> dict:  # noqa: ANN001
    page = session.goto("/dashboard/")
    urls = page.locator("link[rel='stylesheet'], script[src], img[src]").evaluate_all(
        "els => els.map(el => el.href || el.src).filter(Boolean)"
    )
    failures = []
    for url in urls[:100]:
        response = page.request.get(url, timeout=session.timeout_ms)
        if response.status >= 400:
            failures.append(f"{response.status} {url}")
    if failures:
        raise AssertionError("Assets privados rotos: " + "; ".join(failures[:8]))
    return {"assets_checked": len(urls)}
