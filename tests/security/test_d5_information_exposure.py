"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for d5 information exposure in the security domain.
"""

from __future__ import annotations

import secrets

import pytest
from django.conf import settings
from django.test import RequestFactory
from django.views import defaults

from tests.security.production_settings_probe import production_security_settings

API_DOC_PATHS = ["/api/schema/", "/api/docs/", "/api/v1/schema/", "/api/v1/docs/"]

LEAK_MARKERS = ("Traceback", "Exception Type", "SECRET_KEY", "settings.PASSWORD", "django.db.utils")


def _ephemeral_password() -> str:
    """ES: Genera una credencial efímera exclusiva de la ejecución de prueba.

    EN: Generate an ephemeral credential scoped to the test execution.
    """
    return secrets.token_urlsafe(24)


def _assert_no_leak(body: str, label: str):
    for marker in LEAK_MARKERS:
        assert marker not in body, f"{label} expuso {marker}"


def test_debug_is_disabled_outside_local_environments():
    assert settings.DEBUG is False
    assert "*" not in settings.ALLOWED_HOSTS
    assert "testserver" in settings.ALLOWED_HOSTS


def test_session_and_csrf_cookie_flags_are_hardened():
    assert settings.SESSION_COOKIE_HTTPONLY is True
    assert settings.SESSION_COOKIE_SAMESITE == "Lax"
    assert settings.CSRF_COOKIE_SAMESITE == "Lax"
    assert settings.SECURE_CONTENT_TYPE_NOSNIFF is True
    assert settings.SECURE_REFERRER_POLICY == "strict-origin-when-cross-origin"
    assert settings.X_FRAME_OPTIONS == "DENY"

    production = production_security_settings()

    assert production["session_secure"] is True
    assert production["session_name"].startswith("__Host-")
    assert production["csrf_name"].startswith("__Host-")
    assert production["consent_name"].startswith("__Host-")
    assert production["session_path"] == production["csrf_path"] == "/"
    assert production["session_domain"] is production["csrf_domain"] is None
    assert production["expire_at_browser_close"] is True
    assert production["csrf_secure"] is True
    assert production["session_httponly"] is True


@pytest.mark.django_db
@pytest.mark.parametrize("path", API_DOC_PATHS)
def test_api_documentation_is_not_public_by_default(client, path):
    response = client.get(path)

    assert response.status_code in {401, 403}, f"{path} devolvió {response.status_code}"


@pytest.mark.django_db
def test_health_dependencies_endpoint_requires_staff(client):
    response = client.get("/health/dependencies/")

    assert response.status_code in {302, 401, 403}
    assert "admin" in response["Location"] or "login" in response["Location"]


@pytest.mark.django_db
def test_health_live_and_ready_do_not_expose_internals(client):
    for path in ("/health/live/", "/health/ready/"):
        body = client.get(path).content.decode()
        assert "password" not in body.lower()
        assert "postgres://" not in body
        assert "redis://" not in body
        _assert_no_leak(body, path)


@pytest.mark.django_db
def test_media_files_are_not_served_when_debug_is_off(client):
    assert client.get("/media/secret.pdf").status_code == 404
    assert client.get("/static/../.env").status_code in {400, 404}


@pytest.mark.django_db
def test_unknown_urls_render_a_generic_404(client):
    response = client.get("/ruta-que-no-existe-d5/")

    assert response.status_code == 404
    body = response.content.decode()
    _assert_no_leak(body, "404")


def test_generic_500_page_has_no_traceback():
    request = RequestFactory().get("/boom")
    response = defaults.server_error(request)

    body = response.content.decode()
    assert response.status_code == 500
    _assert_no_leak(body, "500")


@pytest.mark.django_db
def test_public_pages_do_not_leak_secret_key(client):
    secret = str(settings.SECRET_KEY)
    for path in ("/", "/accounts/login/"):
        body = client.get(path).content.decode()
        assert secret not in body, f"{path} expuso la clave secreta"
        _assert_no_leak(body, path)


@pytest.mark.django_db
def test_login_response_sets_hardened_session_cookie(django_user_model, client):
    password = _ephemeral_password()
    django_user_model.objects.create_user(username="cookie_check", password=password)
    response = client.post(
        "/accounts/login/",
        {"username": "cookie_check", "password": password},
    )

    assert response.status_code in {200, 302}
    cookie = client.cookies.get(settings.SESSION_COOKIE_NAME)
    assert cookie is not None
    assert cookie["httponly"]
    assert cookie["samesite"] == "Lax"


@pytest.mark.django_db
def test_logout_invalidates_the_session(django_user_model, client):
    password = _ephemeral_password()
    django_user_model.objects.create_user(username="logout_check", password=password)
    client.post("/accounts/login/", {"username": "logout_check", "password": password})
    assert client.get("/dashboard/").status_code in {200, 302}

    client.post("/accounts/logout/")

    assert not client.session.session_key
    assert client.get("/dashboard/customers/").status_code == 302
