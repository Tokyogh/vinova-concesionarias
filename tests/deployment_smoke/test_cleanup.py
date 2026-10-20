"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for cleanup in the deployment_smoke domain.
"""

from __future__ import annotations

from tests.deployment_smoke.helpers.cleanup import cleanup_resources
from tests.deployment_smoke.helpers.runtime import run_check, skip_check

__test__ = False


def run(state, session=None):  # noqa: ANN001
    if not state.resources:
        return skip_check(
            state,
            code="cleanup.no_resources",
            scenario="cleanup",
            title="Limpieza de datos SMOKE",
            message="No se crearon recursos en esta ejecución.",
            required=False,
        )
    if state.config.retain_demo_data:
        return skip_check(
            state,
            code="cleanup.retained",
            scenario="cleanup",
            title="Limpieza de datos SMOKE",
            message="Los datos demo se conservaron mediante confirmación explícita.",
            required=False,
        )
    if session is None:
        raise RuntimeError("La limpieza requiere una sesión autenticada.")
    result = run_check(
        state,
        code="cleanup.resources",
        scenario="cleanup",
        title="Neutralización segura de datos SMOKE",
        callback=lambda: _cleanup(state, session),
    )
    if result.status == "failed":
        state.exit_code = 6
    return result


def _cleanup(state, session) -> dict:  # noqa: ANN001
    errors = cleanup_resources(session, state)
    if errors:
        raise AssertionError("; ".join(errors))
    not_cleaned = [resource.label for resource in state.resources if not resource.cleaned]
    if not_cleaned:
        raise AssertionError("Recursos no neutralizados: " + ", ".join(not_cleaned))
    return {
        "message": (
            "Todos los datos creados quedaron archivados, cancelados, anulados o marcados como perdidos. "
            "Vinova conserva trazabilidad/auditoría por diseño; no se realizó borrado físico."
        ),
        "resources_cleaned": len(state.resources),
    }
