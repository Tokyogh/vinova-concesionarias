"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for 11 portal in the e2e domain.
"""

from __future__ import annotations

import pytest

from apps.accounts.models import PermissionCode, Role, User, UserRole
from apps.customers.models import Customer
from apps.notifications.models import NotificationMessage, NotificationRecipient
from apps.vehicles.models import CustomerVehicle
from tests.e2e.helpers.assertions import assert_controls_are_labeled, assert_no_document_overflow
from tests.e2e.helpers.base import VinovaE2EBase


pytestmark = pytest.mark.e2e


class TestClientPortal(VinovaE2EBase):
    def setUp(self):
        super().setUp()
        permission, _ = PermissionCode.objects.get_or_create(
            code="portal.access",
            defaults={"module": "portal", "name": "Acceso al portal"},
        )
        role = Role.objects.create(code="portal-e2e", name="Cliente portal E2E")
        role.permissions.add(permission)
        self.portal_user = User.objects.create_user(
            username="portal-e2e",
            email="portal-e2e@example.com",
            password=self.password,
        )
        UserRole.objects.create(user=self.portal_user, role=role)
        self.portal_customer = Customer.objects.create(
            first_name="Cliente",
            last_name="Portal E2E",
            email=self.portal_user.email,
            account=self.portal_user,
            assigned_branch=self.branch,
            status=Customer.Status.ACTIVE,
        )
        CustomerVehicle.objects.create(customer=self.portal_customer, vehicle=self.vehicle)
        notification = NotificationMessage.objects.create(
            title="Bienvenida al portal",
            body="Tu cuenta privada está lista.",
            message_type=NotificationMessage.MessageType.SYSTEM,
            related_customer=self.portal_customer,
            dedup_key="portal-e2e-welcome",
        )
        NotificationRecipient.objects.create(
            notification=notification,
            recipient_type=NotificationRecipient.RecipientType.CUSTOMER,
            customer=self.portal_customer,
        )

    def test_portal_responsive_keyboard_accessibility_and_module_gate(self):
        console_errors = []
        page_errors = []
        unexpected_http_errors = []
        expected_missing_route = f"{self.live_server_url}/mi-cuenta/servicios/"
        self.page.on(
            "console",
            lambda message: console_errors.append(message.text) if message.type == "error" else None,
        )
        self.page.on("pageerror", lambda error: page_errors.append(str(error)))
        self.page.on(
            "response",
            lambda response: unexpected_http_errors.append((response.status, response.url))
            if response.status >= 400 and response.url != expected_missing_route
            else None,
        )
        self.page.goto(f"{self.live_server_url}/accounts/login/")
        self.page.locator("input[name='username']").fill(self.portal_user.username)
        self.page.locator("input[name='password']").fill(self.password)
        self.page.get_by_role("button", name="Ingresar").click()
        self.page.wait_for_url(f"{self.live_server_url}/mi-cuenta/")
        self.page.wait_for_load_state("networkidle")
        assert self.page.locator("#main-content").is_visible()
        routes = (
            "/mi-cuenta/",
            "/mi-cuenta/vehiculos/",
            "/mi-cuenta/documentos/",
            "/mi-cuenta/facturas/",
            "/mi-cuenta/notificaciones/",
            "/mi-cuenta/perfil/",
            "/mi-cuenta/configuracion/",
        )
        for viewport in (
            {"width": 390, "height": 844},
            {"width": 768, "height": 1024},
            {"width": 1440, "height": 900},
        ):
            self.page.set_viewport_size(viewport)
            for route in routes:
                response = self.page.goto(f"{self.live_server_url}{route}", wait_until="load")
                assert response is not None and response.status == 200
                assert self.page.locator("#main-content").is_visible()
                assert self.page.locator('.portal-sidebar-nav a[aria-current="page"]').count() == 1
                assert self.page.locator(".portal-sidebar-brand > a").get_attribute("href") == "/"
                assert self.page.locator(".portal-bell svg").count() == 1
                assert self.page.locator(".portal-notification-icon svg").count() == 1
                assert_no_document_overflow(self.page, route, viewport)
                assert_controls_are_labeled(self.page, route)

        self.page.goto(f"{self.live_server_url}/mi-cuenta/", wait_until="load")
        self.page.set_viewport_size({"width": 768, "height": 1024})
        self.page.goto(f"{self.live_server_url}/mi-cuenta/", wait_until="load")
        portal_menu = self.page.get_by_role("button", name="Abrir menú")
        assert portal_menu.is_visible()
        assert self.page.locator("#portal-sidebar").get_attribute("aria-hidden") == "true"
        portal_menu.click()
        assert portal_menu.get_attribute("aria-expanded") == "true"
        assert self.page.locator("#portal-sidebar").get_attribute("aria-hidden") == "false"
        self.page.keyboard.press("Escape")
        assert portal_menu.get_attribute("aria-expanded") == "false"
        assert portal_menu.evaluate("element => element === document.activeElement")

        self.page.set_viewport_size({"width": 1440, "height": 900})
        self.page.goto(f"{self.live_server_url}/mi-cuenta/", wait_until="load")
        assert not portal_menu.is_visible()
        assert self.page.locator("#portal-sidebar").get_attribute("aria-hidden") is None
        assert self.page.get_by_role("heading", name="Actividad reciente").is_visible()
        assert self.page.get_by_text("Bienvenida al portal", exact=True).is_visible()
        contrast_results = self.page.evaluate(
            """
            () => {
              const parse = value => (value.match(/[\\d.]+/g) || []).slice(0, 3).map(Number);
              const luminance = rgb => {
                const channels = rgb.map(value => {
                  const normalized = value / 255;
                  return normalized <= .03928
                    ? normalized / 12.92
                    : Math.pow((normalized + .055) / 1.055, 2.4);
                });
                return .2126 * channels[0] + .7152 * channels[1] + .0722 * channels[2];
              };
              const background = element => {
                let current = element;
                while (current) {
                  const value = getComputedStyle(current).backgroundColor;
                  if (value && value !== 'rgba(0, 0, 0, 0)') return value;
                  current = current.parentElement;
                }
                return 'rgb(255, 255, 255)';
              };
              return [
                '.portal-sidebar-nav a[aria-current="page"]',
                '.portal-metric-card small',
                '.portal-home-panel a',
              ].map(selector => {
                const element = document.querySelector(selector);
                const foreground = luminance(parse(getComputedStyle(element).color));
                const backdrop = luminance(parse(background(element)));
                const ratio = (Math.max(foreground, backdrop) + .05) / (Math.min(foreground, backdrop) + .05);
                return {selector, ratio};
              });
            }
            """
        )
        assert all(result["ratio"] >= 4.5 for result in contrast_results), contrast_results
        self.page.keyboard.press("Tab")
        assert self.page.locator(":focus").count() == 1

        self.page.set_viewport_size({"width": 1440, "height": 900})
        self.page.screenshot(
            path=str(self.artifact_root / "portal-desktop.png"),
            full_page=True,
        )
        assert not console_errors, f"Errores de consola en portal: {console_errors}"
        assert not page_errors, f"Errores JavaScript en portal: {page_errors}"
        assert not unexpected_http_errors, f"Errores HTTP inesperados en portal: {unexpected_http_errors}"

        response = self.page.goto(f"{self.live_server_url}/mi-cuenta/servicios/", wait_until="load")
        assert response is not None and response.status == 404
        console_errors.clear()  # Chromium registra el 404 contractual como error de recurso.

        self.page.set_viewport_size({"width": 390, "height": 844})
        self.page.goto(f"{self.live_server_url}/mi-cuenta/", wait_until="networkidle")
        self.page.get_by_role("button", name="Abrir menú").click()
        self.page.locator(".portal-sidebar-brand > a").focus()
        self.page.locator(".portal-sidebar-brand > a").press("Enter")
        self.page.wait_for_url(f"{self.live_server_url}/")
        assert self.page.locator(".public-hero").is_visible()
        self.page.goto(f"{self.live_server_url}/mi-cuenta/", wait_until="networkidle")
        self.page.screenshot(
            path=str(self.artifact_root / "portal-mobile.png"),
            full_page=True,
        )
        assert not console_errors, f"Errores de consola en portal: {console_errors}"
        assert not page_errors, f"Errores JavaScript en portal: {page_errors}"
        assert not unexpected_http_errors, f"Errores HTTP inesperados en portal: {unexpected_http_errors}"
