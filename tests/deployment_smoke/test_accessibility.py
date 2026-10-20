"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for accessibility in the deployment_smoke domain.
"""

from __future__ import annotations

from tests.deployment_smoke.helpers.assertions import assert_no_overflow, unlabeled_controls
from tests.deployment_smoke.helpers.runtime import run_check

__test__ = False

VIEWPORTS = [(390, 844), (768, 1024), (1440, 900)]
PAGES = [
    "/dashboard/customers/",
    "/dashboard/sales/",
    "/dashboard/inventory/",
    "/dashboard/documents/",
    "/dashboard/",
]


def run(state, session=None):  # noqa: ANN001
    if session is None:
        return
    run_check(
        state,
        code="accessibility.responsive",
        scenario="accessibility",
        title="Responsive, etiquetas y teclado",
        callback=lambda: _check(session),
    )


def _check(session) -> dict:  # noqa: ANN001
    assert session.page is not None
    results = []
    for width, height in VIEWPORTS:
        session.page.set_viewport_size({"width": width, "height": height})
        for route in PAGES:
            session.goto(route)
            assert_no_overflow(session.page)
            unlabeled = unlabeled_controls(session.page)
            if unlabeled:
                raise AssertionError(f"Controles sin etiqueta en {route}: {', '.join(unlabeled[:10])}")
            results.append({"route": route, "viewport": f"{width}x{height}"})
    session.goto("/dashboard/customers/")
    session.page.keyboard.press("Tab")
    focus = session.page.evaluate("() => document.activeElement && document.activeElement !== document.body")
    if not focus:
        raise AssertionError("La navegación por teclado no produjo foco visible.")
    shot = session.screenshot("responsive-accessibility")
    return {"pages_checked": len(results), "evidence": [shot]}
