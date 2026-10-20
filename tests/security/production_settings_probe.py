"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Load production settings in an isolated process with non-secret QA values.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys


def production_security_settings() -> dict[str, object]:
    """Return non-sensitive production flags without reusing the test process settings.

    Importing ``config.settings.production`` over an already-loaded test settings
    module gives a misleading hybrid configuration. A fresh interpreter proves
    that the real production module boots with explicit, independent QA secrets.
    """

    environment = os.environ.copy()
    environment.update(
        {
            "DJANGO_SETTINGS_MODULE": "config.settings.production",
            "VINOVA_QA_IGNORE_PROJECT_ENV": "1",
            "SECRET_KEY": "qa-only-production-probe-secret-key-2026-independent",
            "VINOVA_API_TOKEN_PEPPER": "qa-only-production-probe-token-pepper-2026-independent",
            "VINOVA_WEBHOOK_ALLOW_PRIVATE_NETWORKS": "false",
        }
    )
    script = """
import json
from django.conf import settings

print(json.dumps({
    "session_secure": settings.SESSION_COOKIE_SECURE,
    "csrf_secure": settings.CSRF_COOKIE_SECURE,
    "session_httponly": settings.SESSION_COOKIE_HTTPONLY,
    "coop": settings.SECURE_CROSS_ORIGIN_OPENER_POLICY,
    "save_every_request": settings.SESSION_SAVE_EVERY_REQUEST,
    "session_name": settings.SESSION_COOKIE_NAME,
    "session_path": settings.SESSION_COOKIE_PATH,
    "session_domain": settings.SESSION_COOKIE_DOMAIN,
    "csrf_name": settings.CSRF_COOKIE_NAME,
    "csrf_path": settings.CSRF_COOKIE_PATH,
    "csrf_domain": settings.CSRF_COOKIE_DOMAIN,
    "consent_name": settings.VINOVA_COOKIE_CONSENT_NAME,
    "expire_at_browser_close": settings.SESSION_EXPIRE_AT_BROWSER_CLOSE,
}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
        timeout=20,
    )
    return json.loads(completed.stdout)
