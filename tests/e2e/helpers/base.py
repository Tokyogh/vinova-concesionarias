"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for base in the e2e helpers domain.
"""

from __future__ import annotations

import os
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import Browser, Page, sync_playwright

from apps.privacy.cookies import encode_cookie_preferences
from tests.e2e.helpers.auth import login as perform_login
from tests.e2e.helpers.evidence import create_context, save_context_evidence
from tests.e2e.helpers.factories import create_core_data

os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


class VinovaE2EBase(StaticLiveServerTestCase):
    """Shared isolated browser/database setup for one business scenario."""

    host = "127.0.0.1"
    password = "Vinova-QA-Password-2026!"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.browser_name = os.getenv("VINOVA_E2E_BROWSER", "chromium")
        cls.artifact_root = Path(os.getenv("VINOVA_E2E_ARTIFACT_ROOT", "run/qa/e2e")) / cls.browser_name
        cls.artifact_root.mkdir(parents=True, exist_ok=True)
        cls.playwright = sync_playwright().start()
        browser_type = getattr(cls.playwright, cls.browser_name)
        launch_kwargs = {"headless": True}
        if cls.browser_name == "chromium":
            launch_kwargs["args"] = ["--no-sandbox"]
        executable_path = os.getenv("VINOVA_E2E_EXECUTABLE_PATH", "").strip()
        if executable_path:
            launch_kwargs["executable_path"] = executable_path
        cls.browser: Browser = browser_type.launch(**launch_kwargs)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.browser.close()
            cls.playwright.stop()
        finally:
            super().tearDownClass()

    def setUp(self):
        create_core_data(self)
        self.context = create_context(self.browser, self.artifact_root)
        # ES: Los escenarios que prueban tema, favoritos y vistas guardadas
        # declaran su precondición de consentimiento; la suite de privacidad
        # verifica por separado el rechazo y la revocación en backend.
        # EN: Scenarios covering theme, favorites, and saved views declare their
        # consent precondition; privacy tests separately verify rejection and
        # revocation on the backend.
        self.context.add_cookies(
            [
                {
                    "name": settings.VINOVA_COOKIE_CONSENT_NAME,
                    "value": encode_cookie_preferences(
                        preferences=True,
                        analytics=False,
                        external_media=False,
                    ),
                    "url": self.live_server_url,
                }
            ]
        )
        self.page: Page = self.context.new_page()

    def tearDown(self):
        safe_name = self.id().rsplit(".", 1)[-1]
        save_context_evidence(self.context, self.page, self.artifact_root / safe_name)

    def login(self, user=None):
        perform_login(self.page, self.live_server_url, user or self.admin, self.password)
