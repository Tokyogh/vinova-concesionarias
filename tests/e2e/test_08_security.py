"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for 08 security in the e2e domain.
"""

from __future__ import annotations

import pytest

from tests.e2e.helpers.base import VinovaE2EBase

pytestmark = pytest.mark.e2e


class TestPrivacySecurityAndContinuityFlow(VinovaE2EBase):
    def test_08_privacy_security_continuity_and_audit(self):
        self.login()
        for route in [
            "/dashboard/privacy/",
            "/dashboard/security/",
            "/security/sessions/",
            "/dashboard/continuity/",
            "/dashboard/audit/",
        ]:
            response = self.page.goto(f"{self.live_server_url}{route}")
            assert response is not None and response.status < 400
            assert self.page.locator("main").is_visible()
