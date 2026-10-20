"""ES: Este módulo especifica regresiones ejecutables para el dominio de infraestructura compartida.

EN: This module specifies executable regressions for the common domain.

Contexto existente / Existing context:
Regression coverage for public rate limit v170 in the common domain.
"""

import pytest
from django.core.cache import cache
from django.test import override_settings


pytestmark = pytest.mark.django_db


RATE_LIMIT_CACHE = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "public-rate-limit-v170",
    }
}


@override_settings(
    CACHES=RATE_LIMIT_CACHE,
    VINOVA_PUBLIC_FORM_MAX_SUBMISSIONS=1,
    VINOVA_PUBLIC_FORM_WINDOW_SECONDS=120,
)
def test_public_privacy_form_returns_429_after_limit(client):
    cache.clear()
    first = client.post("/privacy/request/", {}, REMOTE_ADDR="192.0.2.10")
    limited = client.post("/privacy/request/", {}, REMOTE_ADDR="192.0.2.10")

    assert first.status_code != 429
    assert limited.status_code == 429
    assert limited["Retry-After"] == "120"


@override_settings(
    CACHES=RATE_LIMIT_CACHE,
    VINOVA_PUBLIC_FORM_MAX_SUBMISSIONS=1,
    VINOVA_PUBLIC_FORM_WINDOW_SECONDS=120,
)
def test_public_form_scopes_and_client_ips_have_independent_limits(client):
    cache.clear()
    assert client.post("/privacy/request/", {}, REMOTE_ADDR="192.0.2.11").status_code != 429
    assert client.post("/leads/request/", {}, REMOTE_ADDR="192.0.2.11").status_code != 429
    assert client.post("/privacy/request/", {}, REMOTE_ADDR="192.0.2.12").status_code != 429
