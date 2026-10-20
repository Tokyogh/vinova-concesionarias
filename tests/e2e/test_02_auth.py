"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for 02 auth in the e2e domain.
"""

from __future__ import annotations

import pytest

from tests.e2e.helpers.base import VinovaE2EBase

pytestmark = pytest.mark.e2e


class TestAuthenticationAndNavigation(VinovaE2EBase):
    def test_02a_login_split_layout(self):
        self.page.goto(f"{self.live_server_url}/accounts/login/")

        assert self.page.locator(".split-login").count() == 1
        assert self.page.locator(".login-visual").is_visible()
        assert self.page.locator(".login-form-panel").is_visible()
        assert self.page.get_by_role("heading", name="Bienvenido de vuelta").is_visible()
        assert self.page.get_by_role("heading", name="Iniciar sesión").is_visible()

        form = self.page.locator(".login-form-inner form")
        assert form.locator("input[name='username']").count() == 1
        assert form.locator("input[name='password']").count() == 1
        assert self.page.get_by_role("button", name="Ingresar").is_visible()
        assert self.page.locator(".login-form-foot").is_visible()

        assert self.page.evaluate(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
        )

    def test_02b_staff_shell_sidebar_topbar(self):
        self.login()
        self.page.goto(f"{self.live_server_url}/dashboard/")

        sidebar = self.page.locator("#staff-sidebar")
        assert sidebar.is_visible()
        box = sidebar.bounding_box()
        assert 230 <= box["width"] <= 250

        active = self.page.locator('#staff-sidebar .side-nav a[aria-current="page"]')
        assert active.count() == 1
        assert active.first.inner_text().strip() == "Mi dashboard"
        background = active.first.evaluate("el => getComputedStyle(el).backgroundColor")
        assert background == "rgb(0, 107, 199)"

        search = self.page.locator(".topbar-search")
        assert search.count() == 1
        assert search.locator("input[name='q']").count() == 1

        self.page.goto(f"{self.live_server_url}/dashboard/vehicles/")
        assert self.page.locator('#staff-sidebar .side-nav a[aria-current="page"]').inner_text().strip() == "Vehículos"
        assert "Tunland" in self.page.locator("body").inner_text()

        brand = self.page.locator("#staff-sidebar .sidebar-brand-link")
        assert brand.get_attribute("href") == "/"
        brand.focus()
        assert brand.evaluate("element => document.activeElement === element")
        brand.click()
        self.page.wait_for_url(f"{self.live_server_url}/")
        assert self.page.locator(".public-nav-actions .nav-staff").is_visible()
        assert self.page.locator(".public-nav-actions .nav-login").count() == 0

        panel_link = self.page.locator(".public-nav-actions .nav-staff")
        panel_link.focus()
        assert panel_link.evaluate("element => document.activeElement === element")
        panel_link.press("Enter")
        self.page.wait_for_url(f"{self.live_server_url}/dashboard/")
        assert self.page.locator('#staff-sidebar .side-nav a[aria-current="page"]').inner_text().strip() == "Mi dashboard"

        assert self.page.locator(".topbar-branch").count() == 1
        assert self.page.locator(".topbar-branch").inner_text().strip() != ""
        assert self.page.locator(".user-pill").is_visible()
        assert self.page.evaluate(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
        )

    def test_02c_staff_executive_summary(self):
        self.login()
        self.page.goto(f"{self.live_server_url}/dashboard/admin/")

        assert self.page.locator('.adaptive-dashboard[data-dashboard-profile="admin"]').is_visible()
        assert self.page.locator(".dashboard-welcome").is_visible()
        assert self.page.locator(".adaptive-metric").count() >= 4
        assert self.page.locator(".adaptive-widget--actions").is_visible()
        actions = self.page.locator(".dashboard-action")
        assert actions.count() == self.page.locator(".dashboard-action__icon svg").count()
        assert all(not value.strip() for value in self.page.locator(".dashboard-action__icon").all_inner_texts())
        assert self.page.evaluate(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
        )

    def test_02d_staff_brand_alignment_responsive_light_dark(self):
        self.login()
        evidence_root = self.artifact_root / "staff-brand-home-link"

        for theme in ("light", "dark"):
            self.page.goto(f"{self.live_server_url}/dashboard/")
            self.page.evaluate("value => localStorage.setItem('vinova-theme', value)", theme)
            for width, height in ((1440, 900), (390, 844)):
                self.page.set_viewport_size({"width": width, "height": height})
                self.page.reload(wait_until="load")
                if width <= 900:
                    drawer_trigger = self.page.locator('[data-drawer-open="staff-sidebar"]')
                    drawer_trigger.click()
                    self.page.locator("#staff-sidebar.is-open").wait_for(state="visible")

                brand = self.page.locator("#staff-sidebar .sidebar-brand-link")
                mark = brand.locator(".brand-mark")
                copy = brand.locator(".sidebar-brand-copy")
                assert brand.is_visible()
                assert brand.get_attribute("href") == "/"
                assert mark.bounding_box()["width"] == 40
                assert mark.bounding_box()["height"] == 40
                assert abs(
                    mark.bounding_box()["y"] + mark.bounding_box()["height"] / 2
                    - (copy.bounding_box()["y"] + copy.bounding_box()["height"] / 2)
                ) <= 1
                assert copy.evaluate("element => element.scrollWidth <= element.clientWidth")
                assert self.page.evaluate(
                    "document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
                )

                evidence_dir = evidence_root / theme
                evidence_dir.mkdir(parents=True, exist_ok=True)
                self.page.screenshot(path=str(evidence_dir / f"{width}x{height}.png"), full_page=True)

    def test_02_authentication_and_internal_navigation(self):
        self.login()
        routes = [
            "/dashboard/",
            "/dashboard/vehicles/",
            "/dashboard/customers/",
            "/dashboard/inventory/",
            "/dashboard/leads/",
            "/dashboard/sales/",
            "/dashboard/invoices/",
            "/dashboard/documents/",
            "/dashboard/reports/",
            "/dashboard/imports/",
            "/dashboard/privacy/",
            "/dashboard/continuity/",
            "/dashboard/security/",
            "/dashboard/integrations/",
            "/dashboard/help/",
            "/dashboard/quality/",
        ]
        for route in routes:
            response = self.page.goto(f"{self.live_server_url}{route}")
            assert response is not None and response.status < 400, f"Ruta interna falló: {route}"
            assert self.page.locator("#main-content").is_visible()
