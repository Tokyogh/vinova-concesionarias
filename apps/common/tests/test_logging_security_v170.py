"""ES: Este módulo especifica regresiones ejecutables para el dominio de infraestructura compartida.

EN: This module specifies executable regressions for the common domain.

Contexto existente / Existing context:
Regression coverage for logging security v170 in the common domain.
"""

import logging

from apps.common.logging import JsonFormatter, SensitiveDataFilter, redact_sensitive


def test_redaction_covers_json_headers_and_credential_urls():
    source = (
        '{"token": "token-value", "password":"password-value"} '
        "Authorization: Bearer bearer-value "
        "redis://worker:redis-value@redis:6379/0"
    )

    redacted = redact_sensitive(source)

    assert "token-value" not in redacted
    assert "password-value" not in redacted
    assert "bearer-value" not in redacted
    assert "redis-value" not in redacted
    assert redacted.count("***") >= 4


def test_logging_filter_and_json_formatter_never_emit_secret_values():
    record = logging.LogRecord(
        name="security-test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg='request failed: {"api_key": "private-value"}',
        args=(),
        exc_info=None,
    )

    assert SensitiveDataFilter().filter(record) is True
    rendered = JsonFormatter().format(record)
    assert "private-value" not in rendered
