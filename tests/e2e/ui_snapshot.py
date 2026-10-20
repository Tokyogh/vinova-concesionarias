# -*- coding: utf-8 -*-
"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Instrumento de inspección visual UI (no forma parte de la suite E2E).

Captura screenshots de referencia para diagnóstico/composición en
Home, Login, Catálogo y panel staff (claro/oscuro, desktop/móvil).
Uso (QA runner):
  VINOVA_E2E_ACTIVE=1 python -m pytest -q tests/e2e/ui_snapshot.py -s

Artifacts: $VINOVA_E2E_ARTIFACT_ROOT (default run/qa/e2e) / ui-snapshot/
"""
from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import Page

from tests.e2e.helpers.base import VinovaE2EBase
from tests.e2e.helpers.evidence import create_context

SNAPSHOT_DIR = "ui-snapshot"
THEME_KEY = "vinova-theme"

VIEWPORTS = [
    (360, 640), (390, 844), (768, 1024), (1024, 768),
    (1366, 768), (1440, 900), (1920, 1080),
]


def _theme(page: Page, theme: str) -> None:
    page.evaluate("(t)=>localStorage.setItem('vinova-theme', t)", theme)


class UISnapshot(VinovaE2EBase):
    def _snap_dir(self) -> Path:
        base = Path(os.getenv("VINOVA_E2E_ARTIFACT_ROOT", "run/qa/e2e"))
        out = base / SNAPSHOT_DIR
        out.mkdir(parents=True, exist_ok=True)
        return out

    def _snap(self, page: Page, name: str, full: bool = True) -> None:
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(300)
        page.screenshot(path=str(self._snap_dir() / f"{name}.png"), full_page=full, timeout=120_000)

    def _goto(self, page: Page, path: str) -> None:
        page.goto(f"{self.live_server_url}{path}", wait_until="load")
        self._set_theme(page)
        page.reload(wait_until="load")

    def _set_theme(self, page: Page, theme: str | None = None) -> None:
        _theme(page, theme or self.theme)

    def setUp(self):
        super().setUp()
        self.theme = "light"

    def _check_toggle(self, page: Page, name: str) -> None:
        """Valida que el toggle de tema funcione (icon/set/html) y persista."""
        current = page.get_attribute("html", "data-theme")
        page.locator("[data-theme-toggle]").first.click()
        page.wait_for_timeout(150)
        after = page.get_attribute("html", "data-theme")
        stored = page.evaluate("()=>localStorage.getItem('vinova-theme')")
        self.assertEqual(current, "light", "esperaba tema inicial light")
        self.assertEqual(after, "dark", "el toggle no cambió a dark")
        self.assertEqual(stored, "dark", "el toggle no persistió")
        page.reload(wait_until="load")
        persisted = page.get_attribute("html", "data-theme")
        self.assertEqual(persisted, "dark", "el tema no sobrevivió el reload")
        self._snap(page, name)

    def test_home_light_dark(self) -> None:
        page = self.page
        self._goto(page, "/")
        self._snap(page, "01-home-light")
        self._check_toggle(page, "02-home-toggled-dark")

    def test_home_dark_system(self) -> None:
        context = create_context(self.browser, self._snap_dir())
        page = context.new_page()
        try:
            page.emulate_media(color_scheme="dark")
            page.goto(f"{self.live_server_url}/", wait_until="load")
            page.wait_for_timeout(250)
            self._snap(page, "03-home-dark-nonexplicit")
        finally:
            page.close()
            context.close()

    def test_login_light_dark(self) -> None:
        page = self.page
        self._goto(page, "/accounts/login/")
        self._snap(page, "04-login-light")
        self._check_toggle(page, "05-login-toggled-dark")

    def test_catalog_light(self) -> None:
        page = self.page
        self._goto(page, "/vehicles/")
        self._snap(page, "06-catalog-light")

    def test_staff_dashboard(self) -> None:
        self.login(self.admin)
        page = self.page
        self._goto(page, "/")
        self._snap(page, "07-staff-home-light")
        self._goto(page, "/dashboard/vehicles/")
        self._snap(page, "08-staff-vehicles-light")

    def test_mobile_home(self) -> None:
        context = self.browser.new_context(viewport={"width": 390, "height": 844}, locale="es-EC")
        page = context.new_page()
        try:
            self._goto(page, "/")
            self._snap(page, "09-mobile-home-light", full=False)
            overflow = page.evaluate(
                "()=> document.documentElement.scrollWidth > document.documentElement.clientWidth"
            )
            print(f"[snapshot] overflow-x home móvil: {overflow}")
        finally:
            page.close()
            context.close()

    def test_mobile_login(self) -> None:
        context = self.browser.new_context(viewport={"width": 390, "height": 844}, locale="es-EC")
        page = context.new_page()
        try:
            self._goto(page, "/accounts/login/")
            self._snap(page, "10-mobile-login-light", full=False)
            overflow = page.evaluate(
                "()=> document.documentElement.scrollWidth > document.documentElement.clientWidth"
            )
            print(f"[snapshot] overflow-x login móvil: {overflow}")
        finally:
            page.close()
            context.close()

    def test_responsive_overflow_grid(self) -> None:
        """Valida overflow-x y contenido cortado en viewports de referencia."""
        public_paths = ["/", "/vehicles/", "/accounts/login/"]
        self.login(self.admin)
        failures = []
        for w, h in VIEWPORTS:
            context = self.browser.new_context(viewport={"width": w, "height": h}, locale="es-EC")
            page = context.new_page()
            try:
                for path in public_paths:
                    self._goto(page, path)
                    bad = page.evaluate(
                        "()=> { const d=document.documentElement, b=document.body;"
                        " return (d.scrollWidth>d.clientWidth) || (b&&b.scrollWidth>b.clientWidth); }"
                    )
                    print(f"[snapshot] {w}x{h} {path} overflow-x: {bad}")
                    if bad:
                        failures.append((w, h, path))
                page.locator("input[name='username']").fill(self.admin.username)
                page.locator("input[name='password']").fill(self.password)
                page.get_by_role("button", name="Ingresar").click()
                page.wait_for_function("() => window.location.pathname.startsWith('/dashboard/')")
                page.wait_for_load_state("networkidle")
                self.assertTrue(page.locator("#main-content").is_visible())
                self._goto(page, "/dashboard/vehicles/")
                bad = page.evaluate(
                    "()=> { const d=document.documentElement, b=document.body;"
                    " return (d.scrollWidth>d.clientWidth) || (b&&b.scrollWidth>b.clientWidth); }"
                )
                print(f"[snapshot] {w}x{h} /dashboard/vehicles/ overflow-x: {bad}")
                if bad:
                    failures.append((w, h, "/dashboard/vehicles/"))
            finally:
                page.close()
                context.close()
        self.assertEqual(failures, [], f"overflow-x detectado en: {failures}")
