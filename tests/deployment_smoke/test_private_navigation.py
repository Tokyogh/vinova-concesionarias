"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for private navigation in the deployment_smoke domain.
"""

from __future__ import annotations

from tests.deployment_smoke.helpers.runtime import run_check

__test__ = False

ROUTES = [
    "/dashboard/",
    "/dashboard/customers/",
    "/dashboard/vehicles/",
    "/dashboard/inventory/",
    "/dashboard/sales/",
    "/dashboard/documents/",
]


def run(state, session=None):  # noqa: ANN001
    if session is None:
        return
    run_check(
        state,
        code="navigation.private_readonly",
        scenario="navigation",
        title="Navegación privada en modo lectura",
        callback=lambda: _navigate(session),
    )


def _navigate(session) -> dict:  # noqa: ANN001
    visited = []
    for route in ROUTES:
        page = session.goto(route)
        if "/accounts/login/" in page.url:
            raise AssertionError(f"La sesión se perdió al abrir {route}.")
        if page.locator("text=No tienes permisos").count() or page.locator("h1:has-text('403')").count():
            raise AssertionError(f"La cuenta técnica no puede leer {route}.")
        if page.locator("main").count() == 0:
            raise AssertionError(f"{route} no contiene el área principal.")
        visited.append(route)
    shot = session.screenshot("private-navigation")
    return {"routes": visited, "evidence": [shot]}
