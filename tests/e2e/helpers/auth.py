"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for auth in the e2e helpers domain.
"""

from __future__ import annotations

from playwright.sync_api import Page

from apps.accounts.models import User


def login(page: Page, live_server_url: str, user: User, password: str) -> None:
    page.goto(f"{live_server_url}/accounts/login/")
    page.locator("input[name='username']").fill(user.username)
    page.locator("input[name='password']").fill(password)
    page.get_by_role("button", name="Ingresar").click()
    page.wait_for_function("() => window.location.pathname.startsWith('/dashboard/')")
    page.wait_for_load_state("networkidle")

    assert page.locator("#main-content").is_visible()
    assert page.locator("nav[aria-label='Navegación interna']").is_visible()
    assert page.get_by_role("button", name="Salir").is_visible()
    assert page.locator("input[name='username']").count() == 0
    assert page.locator("input[name='password']").count() == 0
