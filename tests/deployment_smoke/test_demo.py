"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for demo in the deployment_smoke domain.
"""

from __future__ import annotations

from tests.deployment_smoke.helpers.runtime import run_check

__test__ = False

DEMO_ROUTES = [
    ("dashboard", "/dashboard/"),
    ("clientes", "/dashboard/customers/"),
    ("vehiculos", "/dashboard/vehicles/"),
    ("inventario", "/dashboard/inventory/"),
    ("crm", "/dashboard/leads/"),
    ("ventas", "/dashboard/sales/"),
    ("facturas", "/dashboard/invoices/"),
    ("documentos", "/dashboard/documents/"),
    ("roles", "/accounts/users/"),
    ("auditoria", "/dashboard/audit/"),
    ("reportes", "/dashboard/reports/"),
]


def run(state, session=None):  # noqa: ANN001
    if session is None:
        return
    run_check(
        state,
        code="demo.enterprise_tour",
        scenario="demo",
        title="Recorrido empresarial ordenado",
        callback=lambda: _tour(session),
    )


def _tour(session) -> dict:  # noqa: ANN001
    visited = []
    evidence = []
    for label, route in DEMO_ROUTES:
        page = session.goto(route)
        if "/accounts/login/" in page.url:
            raise AssertionError(f"La sesión se perdió durante la demostración: {label}.")
        if page.locator("main").count() == 0:
            raise AssertionError(f"El módulo {label} no tiene área principal visible.")
        evidence.append(session.screenshot(f"demo-{label}"))
        visited.append({"module": label, "route": route, "url": page.url})
    return {"modules": visited, "evidence": evidence}
