"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for 10 accessibility in the e2e domain.
"""

from __future__ import annotations

import pytest

from tests.e2e.helpers.assertions import assert_controls_are_labeled, assert_no_document_overflow
from tests.e2e.helpers.base import VinovaE2EBase

pytestmark = pytest.mark.e2e


class TestResponsiveKeyboardAndAccessibility(VinovaE2EBase):
    def test_10_update_center_real_state_without_fake_actions(self):
        self.login()
        route = "/dashboard/continuity/updates/"
        self.page.goto(f"{self.live_server_url}{route}")

        assert self.page.get_by_role("heading", name="Actualizaciones", exact=True).is_visible()
        assert self.page.get_by_text("2.0.0", exact=True).is_visible()
        assert self.page.get_by_text("No disponible", exact=True).is_visible()
        assert self.page.get_by_role("button", name="Actualizar ahora").count() == 0

        evidence_root = self.artifact_root / "n14-update-center"
        for theme, width, height in (("light", 1366, 768), ("dark", 390, 844)):
            self.page.set_viewport_size({"width": width, "height": height})
            self.page.evaluate(
                """theme => {
                  localStorage.setItem('vinova-theme', theme);
                  document.documentElement.setAttribute('data-theme', theme);
                }""",
                theme,
            )
            assert_no_document_overflow(self.page, route, {"width": width, "height": height})
            evidence_dir = evidence_root / theme
            evidence_dir.mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(evidence_dir / f"{width}x{height}.png"), full_page=True)

    def test_10_universal_search_real_entity_and_responsive_palette(self):
        self.login()
        self.page.set_viewport_size({"width": 1366, "height": 768})
        self.page.goto(f"{self.live_server_url}/dashboard/vehicles/")
        self.page.keyboard.press("Control+k")
        search = self.page.locator("#command-palette-input")
        search.fill(self.vehicle.vin)

        option = self.page.locator(
            f'[data-command-palette] .command-palette-option[data-key="entity:vehicle:{self.vehicle.pk}"]'
        )
        option.wait_for(state="visible")
        assert "Vehículo" in option.inner_text()
        assert option.get_attribute("data-href").endswith(f"/dashboard/vehicles/{self.vehicle.pk}/")

        evidence_root = self.artifact_root / "n08-search"
        for theme, width, height in (("light", 1366, 768), ("dark", 390, 844)):
            self.page.set_viewport_size({"width": width, "height": height})
            self.page.evaluate(
                """theme => {
                  localStorage.setItem('vinova-theme', theme);
                  document.documentElement.setAttribute('data-theme', theme);
                }""",
                theme,
            )
            assert_no_document_overflow(self.page, "/dashboard/vehicles/", {"width": width, "height": height})
            evidence_dir = evidence_root / theme
            evidence_dir.mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(evidence_dir / f"{width}x{height}.png"), full_page=True)

        option.click()
        self.page.wait_for_url(f"**/dashboard/vehicles/{self.vehicle.pk}/")
        assert self.vehicle.vin in self.page.locator("body").inner_text()

    def test_10_vinova_assist_authorized_intent_and_safe_deep_link(self):
        self.login()
        self.page.set_viewport_size({"width": 1366, "height": 768})
        self.page.goto(f"{self.live_server_url}/dashboard/vehicles/")
        self.page.keyboard.press("Control+k")
        search = self.page.locator("#command-palette-input")
        search.fill("¿Dónde puedo registrar documentos?")

        assist = self.page.locator("[data-command-palette-assist]")
        assist.wait_for(state="visible")
        assert "autorizada" in assist.inner_text()
        option = self.page.locator('[data-command-palette] .command-palette-option[data-key="assist:upload_document"]')
        assert option.is_visible()
        assert option.get_attribute("data-href").endswith("/dashboard/documents/upload/")

        evidence_root = self.artifact_root / "n07-assist"
        for theme, width, height in (("light", 1366, 768), ("dark", 390, 844)):
            self.page.set_viewport_size({"width": width, "height": height})
            self.page.evaluate(
                """theme => {
                  localStorage.setItem('vinova-theme', theme);
                  document.documentElement.setAttribute('data-theme', theme);
                }""",
                theme,
            )
            assert_no_document_overflow(self.page, "/dashboard/vehicles/", {"width": width, "height": height})
            evidence_dir = evidence_root / theme
            evidence_dir.mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(evidence_dir / f"{width}x{height}.png"), full_page=True)

        search.press("Enter")
        self.page.wait_for_url("**/dashboard/documents/upload/")
        assert self.page.locator("form.documents-form-grid").is_visible()

    def test_10_navigation_intelligent_favorites_recents_and_command_palette(self):
        self.login()
        self.page.set_viewport_size({"width": 1366, "height": 768})
        self.page.goto(f"{self.live_server_url}/dashboard/customers/")

        star = self.page.locator('[data-nav-star="customers"]')
        star.click()
        assert star.get_attribute("aria-pressed") == "true"
        assert star.get_attribute("aria-label").startswith("Quitar")
        favorites = self.page.locator("[data-nav-favorites]")
        assert favorites.is_visible()
        assert favorites.locator('[data-nav-key="customers"]').count() == 1

        self.page.goto(f"{self.live_server_url}/dashboard/vehicles/")
        recents = self.page.locator("[data-nav-recents]")
        assert recents.is_visible()
        assert recents.locator('[data-nav-key="vehicles"]').count() == 1
        assert recents.locator('[data-nav-key="customers"]').count() == 1
        self.page.reload()
        assert self.page.locator('[data-nav-star="customers"]').get_attribute("aria-pressed") == "true"

        self.page.keyboard.press("Control+k")
        palette = self.page.locator("[data-command-palette]")
        trigger = self.page.locator("[data-command-palette-trigger]")
        search = self.page.locator("#command-palette-input")
        assert palette.is_visible()
        assert trigger.get_attribute("aria-expanded") == "true"
        assert search.evaluate("element => element === document.activeElement")
        search.fill("repuestos")
        assert palette.locator(".command-palette-option:visible").count() == 1
        assert search.get_attribute("aria-activedescendant")
        self.page.keyboard.press("Enter")
        self.page.wait_for_url("**/dashboard/inventory/")

        self.page.keyboard.press("Control+k")
        search = self.page.locator("#command-palette-input")
        search.press("Shift+Tab")
        close = palette.locator(".command-palette-close")
        assert close.evaluate("element => element === document.activeElement")
        close.press("Tab")
        assert search.evaluate("element => element === document.activeElement")
        search.press("Escape")
        assert palette.is_hidden()
        assert trigger.get_attribute("aria-expanded") == "false"
        assert trigger.evaluate("element => element === document.activeElement")

        evidence_root = self.artifact_root / "n06-navigation"
        for theme, width, height in (("light", 1366, 768), ("dark", 390, 844)):
            self.page.set_viewport_size({"width": width, "height": height})
            self.page.evaluate(
                """theme => {
                  localStorage.setItem('vinova-theme', theme);
                  document.documentElement.setAttribute('data-theme', theme);
                }""",
                theme,
            )
            self.page.keyboard.press("Control+k")
            assert_no_document_overflow(self.page, "/dashboard/inventory/", {"width": width, "height": height})
            evidence_dir = evidence_root / theme
            evidence_dir.mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(evidence_dir / f"{width}x{height}.png"), full_page=True)
            self.page.keyboard.press("Escape")

    def test_10_filters_20_url_chips_saved_views_and_responsive(self):
        self.login()
        route = "/dashboard/customers/?status=active&sort=name_asc"
        console_errors = []
        self.page.on(
            "console",
            lambda message: console_errors.append(message.text) if message.type == "error" else None,
        )
        evidence_root = self.artifact_root / "n05-filters"
        for theme in ("light", "dark"):
            for width, height in ((1366, 768), (390, 844)):
                viewport = {"width": width, "height": height}
                self.page.set_viewport_size(viewport)
                self.page.goto(f"{self.live_server_url}{route}")
                self.page.evaluate(
                    """theme => {
                      localStorage.setItem('vinova-theme', theme);
                      document.documentElement.setAttribute('data-theme', theme);
                    }""",
                    theme,
                )
                panel = self.page.locator('[data-filter-namespace="customers"]')
                assert panel.is_visible()
                assert panel.locator(".filter-chip").count() == 2
                assert_controls_are_labeled(self.page, route)
                assert_no_document_overflow(self.page, route, viewport)
                evidence_dir = evidence_root / theme
                evidence_dir.mkdir(parents=True, exist_ok=True)
                self.page.screenshot(path=str(evidence_dir / f"{width}x{height}.png"), full_page=True)

        panel = self.page.locator('[data-filter-namespace="customers"]')
        more = panel.locator("[data-filter-more]")
        more.click()
        assert more.get_attribute("aria-expanded") == "true"
        assert panel.locator(".filter-panel-advanced").is_visible()

        self.page.once("dialog", lambda dialog: dialog.accept("Clientes activos"))
        panel.locator("[data-saved-view-save]").click()
        saved = panel.locator("[data-saved-view-select]")
        assert saved.locator("option").count() == 2
        assert saved.input_value()
        panel.locator("[data-saved-view-delete]").click()
        assert saved.locator("option").count() == 1
        assert not console_errors, f"Errores de consola en filtros N05: {console_errors}"

    def test_10_dashboard_visual_21_light_dark_viewports(self):
        self.login()
        console_errors = []
        self.page.on(
            "console",
            lambda message: console_errors.append(message.text) if message.type == "error" else None,
        )
        viewports = (
            (1440, 900),
            (1366, 768),
            (1024, 768),
            (768, 1024),
            (390, 844),
        )
        evidence_root = self.artifact_root / "post-n16-visual-corrections" / "dashboard"
        for theme in ("light", "dark"):
            for width, height in viewports:
                viewport = {"width": width, "height": height}
                self.page.set_viewport_size(viewport)
                self.page.goto(f"{self.live_server_url}/dashboard/")
                self.page.evaluate(
                    """theme => {
                      localStorage.setItem('vinova-theme', theme);
                      document.documentElement.setAttribute('data-theme', theme);
                    }""",
                    theme,
                )
                assert self.page.locator("html").get_attribute("data-theme") == theme
                assert_no_document_overflow(self.page, "/dashboard/", viewport)
                assert self.page.locator(".dashboard-welcome").is_visible()
                assert self.page.locator(".adaptive-metric").count() >= 4
                assert self.page.locator(".adaptive-widget--actions").is_visible()
                evidence_dir = evidence_root / theme
                evidence_dir.mkdir(parents=True, exist_ok=True)
                self.page.screenshot(
                    path=str(evidence_dir / f"{width}x{height}.png"),
                    full_page=True,
                )
        assert not console_errors, f"Errores de consola en dashboard N04: {console_errors}"

    def test_10_responsive_keyboard_and_accessibility_basics(self):
        self.login()
        pages = ["/dashboard/customers/", "/dashboard/sales/", "/dashboard/inventory/"]
        viewports = (
            {"width": 390, "height": 844},
            {"width": 768, "height": 1024},
            {"width": 1440, "height": 900},
        )
        for viewport in viewports:
            self.page.set_viewport_size(viewport)
            for route in pages:
                self.page.goto(f"{self.live_server_url}{route}")
                assert_no_document_overflow(self.page, route, viewport)
                assert_controls_are_labeled(self.page, route)
        self.page.goto(f"{self.live_server_url}/dashboard/customers/")
        self.page.keyboard.press("Tab")
        assert self.page.locator(":focus").count() == 1

    def test_11_staff_mobile_shell_drawer_and_primary_content(self):
        self.login()
        routes = [
            "/dashboard/admin/",
            "/dashboard/vehicles/",
            "/dashboard/inventory/",
            "/dashboard/leads/",
            "/dashboard/sales/",
            "/dashboard/invoices/",
            "/accounts/users/",
        ]
        for width in (320, 360, 390, 430, 768):
            viewport = {"width": width, "height": 844 if width < 600 else 1024}
            self.page.set_viewport_size(viewport)
            for route in routes:
                self.page.goto(f"{self.live_server_url}{route}")
                assert_no_document_overflow(self.page, route, viewport)
                assert self.page.locator("#staff-sidebar").get_attribute("aria-hidden") == "true"
                topbar = self.page.locator(".topbar").bounding_box()
                assert topbar is not None and topbar["y"] < viewport["height"]

        self.page.set_viewport_size({"width": 390, "height": 844})
        self.page.goto(f"{self.live_server_url}/dashboard/admin/")
        menu = self.page.get_by_role("button", name="Menú", exact=True)
        menu.click()
        assert menu.get_attribute("aria-expanded") == "true"
        assert self.page.locator("#staff-sidebar").get_attribute("aria-hidden") == "false"
        assert self.page.locator("body").evaluate("element => element.classList.contains('drawer-open')")
        self.page.get_by_role("button", name="Cerrar menú").click()
        assert menu.get_attribute("aria-expanded") == "false"
        menu.click()
        self.page.locator('[data-drawer-overlay="staff-sidebar"]').click(position={"x": 380, "y": 400})
        assert menu.get_attribute("aria-expanded") == "false"
        menu.click()
        self.page.keyboard.press("Escape")
        assert menu.get_attribute("aria-expanded") == "false"
        assert menu.evaluate("element => element === document.activeElement")

    def test_12_public_mobile_navigation_drawer(self):
        for viewport in ({"width": 390, "height": 844}, {"width": 1024, "height": 768}):
            self.page.set_viewport_size(viewport)
            self.page.goto(f"{self.live_server_url}/")
            menu = self.page.get_by_role("button", name="Menú", exact=True)
            drawer = self.page.locator("#public-nav-drawer")

            assert menu.is_visible()
            assert drawer.get_attribute("aria-hidden") == "true"
            menu.click()
            assert drawer.get_attribute("aria-hidden") == "false"
            assert drawer.get_by_role("link", name="Vehículos", exact=True).is_visible()
            self.page.keyboard.press("Escape")
            assert drawer.get_attribute("aria-hidden") == "true"
            assert menu.evaluate("element => element === document.activeElement")
            assert_no_document_overflow(self.page, "/", viewport)
