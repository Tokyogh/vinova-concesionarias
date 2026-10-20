"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for auth in the deployment_smoke domain.
"""

from __future__ import annotations

from tests.deployment_smoke.helpers.runtime import run_check

__test__ = False


def run(state, session=None):  # noqa: ANN001
    if session is None:
        return
    config = state.config
    run_check(
        state,
        code="auth.login",
        scenario="auth",
        title="Inicio de sesión técnico",
        callback=lambda: _login(session, config.username, config.password),
    )


def _login(session, username: str, password: str) -> dict:  # noqa: ANN001
    session.login(username, password)
    shot = session.screenshot("authenticated-dashboard")
    return {"url": session.page.url, "evidence": [shot]}
