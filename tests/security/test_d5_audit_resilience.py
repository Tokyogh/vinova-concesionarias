"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Security regression tests for failures in the persistent audit sink.
"""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory

from apps.audit.middleware import AuditRequestMiddleware


@pytest.mark.parametrize(
    ("raised", "message"),
    (
        (PermissionDenied("denied"), "autorización denegada"),
        (RuntimeError("application failed"), "error de servidor"),
    ),
)
def test_audit_sink_failure_is_logged_without_masking_original_exception(caplog, raised, message):
    request = RequestFactory().get("/dashboard/security-probe/")
    request.user = None
    middleware = AuditRequestMiddleware(lambda _request: (_ for _ in ()).throw(raised))

    with (
        patch("apps.audit.services.audit_log", side_effect=RuntimeError("audit sink unavailable")),
        caplog.at_level(logging.ERROR, logger="apps.audit.middleware"),
        pytest.raises(type(raised), match=str(raised)),
    ):
        middleware(request)

    assert message in caplog.text
    assert "audit sink unavailable" in caplog.text
