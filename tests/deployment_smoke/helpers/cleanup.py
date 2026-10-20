"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for cleanup in the deployment_smoke helpers domain.
"""

from __future__ import annotations

from tests.deployment_smoke.helpers.browser import BrowserSession
from tests.deployment_smoke.helpers.models import RunState


def cleanup_resources(session: BrowserSession, state: RunState) -> list[str]:
    errors: list[str] = []
    assert session.page is not None
    for resource in reversed(state.resources):
        if resource.cleaned:
            continue
        try:
            session.goto(resource.detail_url)
            form = session.page.locator(f"form[action='{resource.cleanup_action}']")
            if form.count() == 0:
                form = session.page.locator(f"form[action$='{resource.cleanup_action}']")
            if form.count() == 0:
                raise AssertionError(f"No se encontró la acción de limpieza para {resource.label}.")
            if resource.kind == "lead":
                select = form.locator("select[name='status']")
                if select.count() == 0:
                    raise AssertionError("El formulario del lead no permite marcarlo como perdido.")
                select.select_option("lost")
                form.locator("textarea[name='lost_reason']").fill(f"Limpieza automática {state.config.marker}")
            elif resource.kind == "sale":
                note = form.locator("textarea[name='note'], input[name='note']")
                if note.count():
                    note.first.fill(f"Limpieza automática {state.config.marker}")
            elif resource.kind == "invoice":
                reason = form.locator("textarea[name='reason'], input[name='reason']")
                if reason.count() == 0:
                    raise AssertionError("El formulario de factura no permite indicar motivo de anulación.")
                reason.first.fill(f"Limpieza automática {state.config.marker}")
            with session.page.expect_navigation(wait_until="domcontentloaded"):
                form.get_by_role("button", name=resource.cleanup_button).click()
            resource.cleaned = True
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{resource.kind} {resource.label}: {type(exc).__name__}: {exc}")
    return errors
