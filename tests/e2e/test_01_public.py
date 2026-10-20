"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for 01 public in the e2e domain.
"""

from __future__ import annotations

import re

import pytest

from apps.branches.models import Branch
from apps.leads.models import Lead
from tests.e2e.helpers.assertions import assert_controls_are_labeled, assert_no_document_overflow
from tests.e2e.helpers.base import VinovaE2EBase
from tests.e2e.helpers.forms import submit_and_wait_for_url, submit_form_and_wait_for_url

pytestmark = pytest.mark.e2e


class TestPublicCatalogAndRequests(VinovaE2EBase):
    def test_00_public_auth_light_dark_responsive_matrix(self):
        routes = {
            "home": "/",
            "catalog": "/vehicles/",
            "detail": f"/vehicles/{self.vehicle.public_slug}/",
            "services": "/servicios/#servicios",
            "about": "/nosotros/#nosotros",
            "institutions": "/instituciones/",
            "contact": "/leads/request/",
            "login": "/accounts/login/",
        }
        active_sections = {
            "home": None,
            "catalog": "Vehículos",
            "detail": "Vehículos",
            "services": "Servicios",
            "about": "Nosotros",
            "institutions": "Instituciones",
            "contact": "Contacto",
            "login": None,
        }
        viewports = ((1440, 900), (1366, 768), (1024, 768), (768, 1024), (390, 844))
        console_errors = []
        self.page.on(
            "console",
            lambda message: console_errors.append(message.text) if message.type == "error" else None,
        )
        self.page.goto(f"{self.live_server_url}/")
        evidence_root = self.artifact_root / "post-n16-visual-corrections" / "public-auth"

        for theme in ("light", "dark"):
            self.page.evaluate("theme => localStorage.setItem('vinova-theme', theme)", theme)
            for width, height in viewports:
                viewport = {"width": width, "height": height}
                self.page.set_viewport_size(viewport)
                for name, route in routes.items():
                    self.page.goto(f"{self.live_server_url}{route}", wait_until="load")
                    assert self.page.locator("html").get_attribute("data-theme") == theme
                    assert_no_document_overflow(self.page, route, viewport)
                    assert_controls_are_labeled(self.page, route)
                    public_nav = self.page.locator(".public-nav")
                    if public_nav.count():
                        active = public_nav.locator('a[aria-current="page"]')
                        expected = active_sections[name]
                        assert active.count() == (1 if expected else 0)
                        if expected:
                            assert (active.text_content() or "").strip() == expected
                    if name == "home":
                        hero = self.page.locator(".public-hero")
                        content = hero.locator(".public-hero-content")
                        media = hero.locator(".hero-media")
                        image_box = hero.locator(".hero-image")
                        heading = hero.locator("h1")
                        actions = hero.locator(".hero-actions")
                        header = self.page.locator(".public-header")
                        hero_box = hero.bounding_box()
                        content_box = content.bounding_box()
                        media_box = media.bounding_box()
                        image_box_geometry = image_box.bounding_box()
                        heading_box = heading.bounding_box()
                        actions_box = actions.bounding_box()
                        header_box = header.bounding_box()
                        image_effects = image_box.evaluate(
                            """element => {
                              const style = getComputedStyle(element);
                              return {
                                clipPath: style.clipPath,
                                maskImage: style.maskImage,
                                webkitMaskImage: style.webkitMaskImage,
                                display: style.display,
                                before: getComputedStyle(element, '::before').content,
                                after: getComputedStyle(element, '::after').content,
                              };
                            }"""
                        )
                        assert hero.locator(".hero-photo-overlay").count() == 0
                        assert hero.locator(".hero-photo-veil").count() == 0
                        assert image_effects["clipPath"] == "none"
                        assert image_effects["maskImage"] != "none"
                        assert image_effects["webkitMaskImage"] != "none"
                        assert "linear-gradient" in image_effects["maskImage"]
                        assert image_effects["display"] == "block"
                        assert image_effects["before"] == "none"
                        assert image_effects["after"] == "none"
                        assert image_box.evaluate("element => getComputedStyle(element).aspectRatio") == "auto"
                        assert abs(image_box_geometry["width"] - media_box["width"]) <= 1
                        assert abs(image_box_geometry["height"] - media_box["height"]) <= 1
                        assert hero.locator('[data-asset-slot="hero-home"] img').evaluate(
                            "image => image.complete && image.naturalWidth > 0"
                        )
                        assert hero.locator('[data-asset-slot="hero-home"] img').evaluate(
                            "image => getComputedStyle(image).objectFit"
                        ) == "contain"
                        if width > 900:
                            assert abs(media_box["x"] - hero_box["x"]) <= 1
                            assert abs(media_box["y"] - hero_box["y"]) <= 1
                            assert abs(media_box["width"] - hero_box["width"]) <= 1
                            assert abs(media_box["height"] - hero_box["height"]) <= 1
                            assert abs(image_box_geometry["y"] - hero_box["y"]) <= 1
                            assert abs(image_box_geometry["x"] + image_box_geometry["width"] - (hero_box["x"] + hero_box["width"])) <= 1
                            assert media_box["y"] < actions_box["y"] + actions_box["height"]
                            assert heading_box["y"] >= header_box["y"] + header_box["height"] - 1
                            assert content_box["y"] >= media_box["y"]
                            assert content_box["y"] + content_box["height"] <= media_box["y"] + media_box["height"]
                        else:
                            assert media_box["y"] >= actions_box["y"] + actions_box["height"] - 1
                    self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    assert self.page.locator("img").evaluate_all(
                        """async images => {
                          const decoded = await Promise.all(images.map(async image => {
                            try {
                              await image.decode();
                              return image.complete && image.naturalWidth > 0;
                            } catch (_) {
                              return false;
                            }
                          }));
                          return decoded.every(Boolean);
                        }"""
                    )
                    self.page.evaluate("window.scrollTo(0, 0)")
                    evidence_dir = evidence_root / theme / f"{width}x{height}"
                    evidence_dir.mkdir(parents=True, exist_ok=True)
                    self.page.screenshot(path=str(evidence_dir / f"{name}.png"), full_page=True)

        assert not console_errors, f"Errores de consola en Public/Auth N10: {console_errors}"

    def test_00_public_brand_returns_home_with_keyboard(self):
        self.page.goto(f"{self.live_server_url}/vehicles/")

        brand = self.page.locator(".public-brand")
        assert brand.get_attribute("href") == "/"
        brand.focus()
        assert brand.evaluate("element => document.activeElement === element")
        brand.press("Enter")
        self.page.wait_for_url(f"{self.live_server_url}/")

    def test_00_public_institutions_filters_details_and_responsive_layout(self):
        self.branch.address = "Av. Matriz QA"
        self.branch.province = "Pichincha"
        self.branch.opening_hours = "Lunes a viernes"
        self.branch.services = ["Venta de vehículos", "Financiamiento"]
        self.branch.latitude = "-0.180653"
        self.branch.longitude = "-78.467834"
        self.branch.save()
        Branch.objects.create(
            company=self.company,
            name="Institución QA",
            code="QA-INST",
            branch_type=Branch.BranchType.AFFILIATED_INSTITUTION,
            city="Cuenca",
            province="Azuay",
            address="Centro QA",
            is_public=True,
            is_active=True,
        )

        self.page.goto(f"{self.live_server_url}/instituciones/", wait_until="load")
        assert self.page.locator('.public-nav a[aria-current="page"]').inner_text().strip() == "Instituciones"
        assert self.page.locator("[data-establishment-card]").count() == 2
        assert self.page.locator("[data-establishment-detail]:not(.is-hidden)").count() == 1
        self.page.locator("#institutionSearch").fill("Cuenca")
        assert self.page.locator("[data-establishment-card]:visible").count() == 1
        self.page.locator("[data-establishment-card]:visible").press("Enter")
        assert self.page.locator("[data-establishment-detail]:not(.is-hidden) h2").inner_text() == "Institución QA"
        self.page.locator("#institutionSearch").fill("sin coincidencias qa")
        assert self.page.locator("[data-filter-empty]").is_visible()
        self.page.locator("#institutionSearch").fill("")
        self.page.locator("#institutionTypeSelect").select_option("dealership")
        assert self.page.locator("[data-establishment-card]:visible").count() == 1
        assert "tipo=dealership" in self.page.url
        clear_filters = self.page.locator("[data-clear-institution-filters]")
        assert clear_filters.is_visible()
        clear_filters.click()
        assert self.page.locator("[data-establishment-card]:visible").count() == 2
        assert self.page.locator("#institutionTypeSelect").input_value() == ""
        assert "tipo=" not in self.page.url
        assert clear_filters.is_hidden()

        dealership_card = self.page.locator('[data-institution-filter="dealership"]')
        dealership_card.click()
        assert self.page.locator("[data-establishment-card]:visible").count() == 1
        assert dealership_card.get_attribute("aria-current") == "true"
        dealership_card.click()
        assert self.page.locator("[data-establishment-card]:visible").count() == 2
        assert dealership_card.get_attribute("aria-current") is None

        for viewport in ({"width": 1440, "height": 900}, {"width": 768, "height": 1024}, {"width": 390, "height": 844}):
            self.page.set_viewport_size(viewport)
            assert_no_document_overflow(self.page, "/instituciones/", viewport)
            assert_controls_are_labeled(self.page, "/instituciones/")

    def _assert_theme_toggle(self, theme, next_theme):
        toggle = self.page.locator("[data-theme-toggle]").first
        expected_label = f"Cambiar a modo {next_theme}"
        assert self.page.locator("html").get_attribute("data-theme") == theme
        assert toggle.get_attribute("aria-label") == expected_label
        assert toggle.get_attribute("title") == expected_label
        assert toggle.locator(".ico-sun").is_visible() is (theme == "dark")
        assert toggle.locator(".ico-moon").is_visible() is (theme == "light")

    def test_00_theme_toggle_initial_state_and_preference(self):
        self.page.goto(f"{self.live_server_url}/")

        self.page.evaluate("localStorage.setItem('vinova-theme', 'dark')")
        self.page.reload(wait_until="load")
        self._assert_theme_toggle("dark", "claro")

        self.page.emulate_media(color_scheme="light")
        self._assert_theme_toggle("dark", "claro")

        self.page.locator("[data-theme-toggle]").first.click()
        self._assert_theme_toggle("light", "oscuro")
        assert self.page.evaluate("localStorage.getItem('vinova-theme')") == "light"

        self.page.evaluate("localStorage.removeItem('vinova-theme')")
        self.page.emulate_media(color_scheme="dark")
        self.page.reload(wait_until="load")
        self._assert_theme_toggle("dark", "claro")

        self.page.emulate_media(color_scheme="light")
        self.page.wait_for_function("document.documentElement.dataset.theme === 'light'")
        self._assert_theme_toggle("light", "oscuro")

    def test_01_public_services_hero_and_items(self):
        self.page.goto(f"{self.live_server_url}/")

        home_hero = self.page.locator('[data-asset-slot="hero-home"] img')
        assert home_hero.count() == 1
        assert "02_hero-home" in (home_hero.get_attribute("src") or "")

        hero = self.page.locator("#servicios")
        assert hero.evaluate("e => e.tagName") == "SECTION"
        assert self.page.locator(".service-hero-content h2").inner_text().split() == [
            "Tu", "vehículo", "siempre", "en", "las", "mejores", "manos",
        ]
        assert self.page.locator(".service-hero-actions a").count() == 2
        assert self.page.locator(".service-hero-actions a").first.is_visible()
        hero.scroll_into_view_if_needed()
        workshop_image = hero.locator('[data-asset-slot="workshop-services"] img')
        assert workshop_image.count() == 1
        workshop_image.evaluate("image => image.decode()")
        assert workshop_image.evaluate("image => image.complete && image.naturalWidth > 0")

        items = self.page.locator(".services-body .service-item")
        assert items.count() == 4
        titles = [items.nth(i).locator("h3").inner_text().strip() for i in range(4)]
        assert titles == [
            "Servicio técnico", "Repuestos originales",
            "Agendamiento en línea", "Asesoría postventa",
        ]
        for index, accent in enumerate(("service-blue", "service-cyan", "service-green", "service-violet")):
            assert accent in (items.nth(index).locator(".service-icon").get_attribute("class") or "")
            assert items.nth(index).locator(".service-icon svg").count() == 1
            assert items.nth(index).locator("p").inner_text().strip() != ""

        about = self.page.locator("#nosotros")
        assert about.locator(".about-content h2").is_visible()
        assert about.locator(".about-content .btn").is_visible()
        assert about.locator(".about-media").is_visible()
        about.scroll_into_view_if_needed()
        showroom_image = about.locator('[data-asset-slot="showroom-about"] img')
        assert showroom_image.count() == 1
        showroom_image.evaluate("image => image.decode()")
        assert showroom_image.evaluate("image => image.complete && image.naturalWidth > 0")

        stats = about.locator(".about-stats article")
        assert stats.count() == 4
        for index in range(4):
            value = stats.nth(index).locator("strong").inner_text().strip()
            assert value.isdigit(), f"cifra publica no numerica: {value!r}"
            assert stats.nth(index).locator("span").inner_text().strip() != ""

    def test_02_public_catalog_filters_and_ordering(self):
        self.page.goto(f"{self.live_server_url}/vehicles/")

        assert self.page.locator("#catalog-filters").count() == 1
        assert self.page.locator(".catalog-hero-media .catalog-editorial").count() == 3
        assert self.page.locator(".catalog-sidebar").is_visible()
        assert self.page.locator(".vehicle-card").count() == 1
        assert self.page.locator(".vehicle-card .vehicle-image-placeholder").count() == 1
        assert "1" in self.page.locator(".catalog-count").inner_text()

        self.page.locator("select[name='marca']").select_option(str(self.brand.pk))
        submit_form_and_wait_for_url(
            self.page,
            self.page.locator("#catalog-filters"),
            re.compile(rf".*/vehicles/\?.*marca={self.brand.pk}.*"),
        )
        assert self.page.locator(".vehicle-card").count() == 1

        self.page.goto(f"{self.live_server_url}/vehicles/?precio_min=99999999")
        assert self.page.locator(".vehicle-card").count() == 0
        assert self.page.locator(".catalog-empty").is_visible()

        self.page.goto(f"{self.live_server_url}/vehicles/")
        self.page.locator("select[name='orden']").select_option("precio-asc")
        self.page.wait_for_url(re.compile(r".*/vehicles/\?.*orden=precio-asc.*"))
        assert self.page.locator(".vehicle-card").count() == 1

        self.page.goto(f"{self.live_server_url}/vehicles/?marca=999999")
        assert self.page.locator(".catalog-empty").is_visible()

    def test_03_public_catalog_vehicle_favorite_is_local_state(self):
        self.page.goto(f"{self.live_server_url}/vehicles/")

        favorite = self.page.locator(".vehicle-favorite").first
        assert favorite.get_attribute("aria-pressed") == "false"
        favorite.click()
        assert favorite.get_attribute("aria-pressed") == "true"

        self.page.reload(wait_until="load")
        assert self.page.locator(".vehicle-favorite").first.get_attribute("aria-pressed") == "true"

        self.page.locator(".vehicle-favorite").first.click()
        assert self.page.locator(".vehicle-favorite").first.get_attribute("aria-pressed") == "false"
        self.page.reload(wait_until="load")
        assert self.page.locator(".vehicle-favorite").first.get_attribute("aria-pressed") == "false"

    def test_04_public_vehicle_detail_page(self):
        self.page.goto(f"{self.live_server_url}/vehicles/")
        detail_link = self.page.locator(".vehicle-details-link").first
        assert detail_link.is_visible()
        detail_link.click()
        self.page.wait_for_url(re.compile(r".*/vehicles/[a-z0-9-]+/$"))

        assert self.page.get_by_role("heading", level=1).inner_text().strip() != ""
        assert self.page.locator(".vehicle-stage").is_visible()
        assert self.page.locator(".vehicle-summary").is_visible()
        assert self.page.locator("[data-detail-tab]").count() == 4

        self.page.locator('[data-detail-tab="equipment"]').click()
        assert self.page.locator('[data-detail-panel="equipment"]').is_visible()
        assert self.page.locator('[data-detail-panel="features"]').is_hidden()

        self.page.locator('[data-detail-tab="gallery"]').click()
        assert self.page.locator('[data-detail-panel="gallery"]').is_visible()

        cta = self.page.locator(".vehicle-summary-actions a").first
        assert cta.get_attribute("href").startswith("/leads/")

        self.page.goto(f"{self.live_server_url}/vehicles/no-existe/")
        assert self.page.locator("h1").count() >= 1

    def test_05_public_contact_three_zones(self):
        self.page.goto(f"{self.live_server_url}/leads/request/")

        layout = self.page.locator(".public-contact-layout")
        assert layout.count() == 1

        channels = self.page.locator(".contact-channel h3")
        assert channels.count() >= 3
        titles = [channels.nth(i).inner_text().strip() for i in range(3)]
        assert titles == ["Ventas", "Postventa", "Matriz"]

        form = self.page.locator(".lead-public-form")
        for field in ("full_name", "email", "phone", "request_type", "message"):
            assert form.locator(f"[name='{field}']").count() == 1, field
        assert self.page.get_by_role("button", name="Enviar solicitud").is_visible()

        assert self.page.locator(".contact-photo").is_visible()
        branches = self.page.locator(".contact-branches h2")
        assert branches.inner_text().strip() == "Nuestras sucursales"
        assert self.page.locator(".contact-branch-list li").count() >= 1

        assert self.page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")

    def test_01_public_catalog_and_requests(self):
        self.page.goto(f"{self.live_server_url}/")
        assert self.page.get_by_role("main").is_visible()
        self.page.goto(f"{self.live_server_url}/vehicles/")
        assert self.page.locator("input[name='q']").count() == 1
        self.page.locator("input[name='q']").fill("Tunland")
        submit_form_and_wait_for_url(
            self.page,
            self.page.locator("form").first,
            re.compile(r".*/vehicles/\?.*q=Tunland.*"),
        )
        assert "Tunland QA" in self.page.locator("body").inner_text()

        self.page.goto(f"{self.live_server_url}/leads/request/")
        self.page.locator("select[name='request_type']").select_option(Lead.RequestType.INFORMATION)
        self.page.locator("input[name='full_name']").fill("Cliente Público QA")
        self.page.locator("input[name='email']").fill("publico.qa@example.com")
        self.page.locator("select[name='preferred_contact_method']").select_option("email")
        consent = self.page.locator("input[name='consent_data_processing']")
        if consent.count():
            consent.check()
        submit_and_wait_for_url(
            self.page,
            self.page.get_by_role("button", name="Enviar solicitud"),
            re.compile(r".*/leads/request/success/.*"),
        )

        self.page.wait_for_function("() => window.location.pathname.startsWith('/leads/request/success/')")

        assert Lead.objects.filter(email="publico.qa@example.com", full_name="Cliente Público QA").exists()
        assert self.page.locator('[data-testid="lead-request-success"]').is_visible()
        assert self.page.get_by_role("heading", name="Gracias por contactarnos").is_visible()
