"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for browser in the deployment_smoke helpers domain.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urljoin

if TYPE_CHECKING:
    from playwright.sync_api import Browser, BrowserContext, Page, Playwright


class BrowserDependencyError(RuntimeError):
    """Playwright o el navegador solicitado no están disponibles."""


class BrowserSession:
    def __init__(
        self,
        *,
        base_url: str,
        browser_name: str,
        timeout_seconds: int,
        headless: bool,
        output_dir: Path,
        record_video: bool,
        verify_tls: bool = True,
        shared_browser: Browser | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.browser_name = browser_name
        self.timeout_ms = timeout_seconds * 1000
        self.headless = headless
        self.output_dir = output_dir
        self.record_video = record_video
        self.verify_tls = verify_tls
        self.shared_browser = shared_browser
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self._owns_playwright = False
        self._owns_browser = False
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.screenshot_count = 0

    def __enter__(self) -> "BrowserSession":
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.shared_browser is not None:
            self.browser = self.shared_browser
        else:
            try:
                from playwright.sync_api import sync_playwright
            except ModuleNotFoundError as exc:
                raise BrowserDependencyError(
                    "Playwright no está instalado. Instala requirements/local.txt y los navegadores requeridos."
                ) from exc
            self.playwright = sync_playwright().start()
            self._owns_playwright = True
            browser_type = getattr(self.playwright, self.browser_name)
            try:
                self.browser = browser_type.launch(headless=self.headless)
                self._owns_browser = True
            except Exception as exc:  # noqa: BLE001
                message = str(exc)
                if "Executable doesn't exist" in message or "playwright install" in message.lower():
                    raise BrowserDependencyError(
                        f"El navegador Playwright {self.browser_name} no está instalado. "
                        f"Ejecuta: python -m playwright install {self.browser_name}."
                    ) from exc
                raise
        context_kwargs: dict[str, object] = {
            "ignore_https_errors": not self.verify_tls,
            "viewport": {"width": 1440, "height": 900},
            "locale": "es-EC",
        }
        if self.record_video:
            video_dir = self.output_dir / "videos"
            video_dir.mkdir(parents=True, exist_ok=True)
            context_kwargs["record_video_dir"] = str(video_dir)
            context_kwargs["record_video_size"] = {"width": 1440, "height": 900}
        self.context = self.browser.new_context(**context_kwargs)
        self.context.set_default_timeout(self.timeout_ms)
        self.context.set_default_navigation_timeout(self.timeout_ms)
        traces = self.output_dir / "traces"
        traces.mkdir(parents=True, exist_ok=True)
        self.context.tracing.start(screenshots=True, snapshots=True, sources=False)
        self.page = self.context.new_page()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:  # noqa: ANN001
        try:
            if self.context:
                trace_path = self.output_dir / "traces" / "trace.zip"
                self.context.tracing.stop(path=str(trace_path))
        finally:
            if self.context:
                self.context.close()
            if self.browser and self._owns_browser:
                self.browser.close()
            if self.playwright and self._owns_playwright:
                self.playwright.stop()

    def url(self, path: str) -> str:
        return urljoin(self.base_url + "/", path.lstrip("/"))

    def goto(self, path: str) -> Page:
        assert self.page is not None
        response = self.page.goto(self.url(path), wait_until="domcontentloaded")
        if response is None:
            raise AssertionError(f"La navegación no devolvió respuesta: {path}")
        if response.status >= 500:
            raise AssertionError(f"La ruta {path} respondió HTTP {response.status}.")
        return self.page

    def screenshot(self, label: str, *, full_page: bool = True) -> str:
        assert self.page is not None
        self.screenshot_count += 1
        safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", label).strip("-").lower() or "capture"
        screenshots = self.output_dir / "screenshots"
        screenshots.mkdir(parents=True, exist_ok=True)
        path = screenshots / f"{self.screenshot_count:02d}-{safe}.png"
        self.page.screenshot(path=str(path), full_page=full_page)
        return str(path.relative_to(self.output_dir))

    def login(self, username: str, password: str) -> None:
        if not username or not password:
            raise ValueError("Faltan VINOVA_SMOKE_USERNAME/VINOVA_SMOKE_PASSWORD.")
        page = self.goto("/accounts/login/")
        page.locator("input[name='username']").fill(username)
        page.locator("input[name='password']").fill(password)
        with page.expect_navigation(wait_until="domcontentloaded"):
            page.locator("form").get_by_role("button").click()
        if "/accounts/login/" in page.url or page.locator("input[name='password']").count():
            raise AssertionError("El inicio de sesión no creó una sesión autenticada.")

    def logout(self) -> None:
        assert self.page is not None
        page = self.page
        if page.locator("form[action$='/accounts/logout/']").count() == 0:
            self.goto("/dashboard/")
        form = page.locator("form[action$='/accounts/logout/']")
        if form.count() == 0:
            raise AssertionError("No se encontró el formulario seguro de cierre de sesión.")
        with page.expect_navigation(wait_until="domcontentloaded"):
            form.get_by_role("button").click()
        if "/accounts/login/" not in page.url:
            raise AssertionError("El cierre de sesión no redirigió al login.")
