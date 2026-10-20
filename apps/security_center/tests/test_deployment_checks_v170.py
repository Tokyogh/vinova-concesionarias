"""ES: Este módulo especifica regresiones ejecutables para el dominio de seguridad.

EN: This module specifies executable regressions for the security center domain.

Contexto existente / Existing context:
Regression coverage for deployment checks v170 in the security_center domain.
"""

import os
from unittest.mock import patch

from django.test import override_settings

from apps.security_center.checks import vinova_security_checks


SECURE_PRODUCTION = {
    "SECRET_KEY": "secure-production-secret",
    "DEBUG": False,
    "SECURE_SSL_REDIRECT": True,
    "SECURE_HSTS_SECONDS": 31536000,
    "SESSION_COOKIE_SECURE": True,
    "SESSION_COOKIE_HTTPONLY": True,
    "CSRF_COOKIE_SECURE": True,
    "SESSION_COOKIE_NAME": "__Host-vinova_session",
    "SESSION_COOKIE_PATH": "/",
    "SESSION_COOKIE_DOMAIN": None,
    "CSRF_COOKIE_NAME": "__Host-vinova_csrf",
    "CSRF_COOKIE_PATH": "/",
    "CSRF_COOKIE_DOMAIN": None,
    "VINOVA_COOKIE_CONSENT_NAME": "__Host-vinova_cookie_preferences",
    "SECURE_CONTENT_TYPE_NOSNIFF": True,
    "ALLOWED_HOSTS": ["vinova.example"],
    "CSRF_TRUSTED_ORIGINS": ["https://vinova.example"],
    "CORS_ALLOW_ALL_ORIGINS": False,
}


def production_check_ids(**overrides):
    configured = {**SECURE_PRODUCTION, **overrides}
    with patch.dict(os.environ, {"DJANGO_SETTINGS_MODULE": "config.settings.production"}), override_settings(**configured):
        return {issue.id for issue in vinova_security_checks(None)}


def test_secure_production_settings_pass_custom_checks(settings):
    assert production_check_ids(MIDDLEWARE=settings.MIDDLEWARE) == set()


def test_production_checks_reject_insecure_transport_and_cookie_settings(settings):
    ids = production_check_ids(
        MIDDLEWARE=settings.MIDDLEWARE,
        DEBUG=True,
        SECURE_SSL_REDIRECT=False,
        SECURE_HSTS_SECONDS=0,
        SESSION_COOKIE_SECURE=False,
        SESSION_COOKIE_HTTPONLY=False,
        CSRF_COOKIE_SECURE=False,
    )

    assert {"vinova_security.E002", "vinova_security.E003", "vinova_security.E004"}.issubset(ids)
    assert {"vinova_security.E005", "vinova_security.E006", "vinova_security.E009"}.issubset(ids)


def test_production_checks_reject_wildcard_hosts_origins_cors_and_missing_middleware(settings):
    middleware = [
        item
        for item in settings.MIDDLEWARE
        if item
        not in {
            "django.middleware.csrf.CsrfViewMiddleware",
            "apps.security_center.middleware.SecurityHeadersMiddleware",
        }
    ]
    ids = production_check_ids(
        MIDDLEWARE=middleware,
        ALLOWED_HOSTS=["*"],
        CSRF_TRUSTED_ORIGINS=["http://vinova.example"],
        CORS_ALLOW_ALL_ORIGINS=True,
    )

    assert {
        "vinova_security.E007",
        "vinova_security.E008",
        "vinova_security.E010",
        "vinova_security.E011",
        "vinova_security.E012",
    }.issubset(ids)


def test_production_checks_reject_cookie_prefix_contract_breakage(settings):
    ids = production_check_ids(
        MIDDLEWARE=settings.MIDDLEWARE,
        SESSION_COOKIE_NAME="sessionid",
        CSRF_COOKIE_DOMAIN=".example.com",
        VINOVA_COOKIE_CONSENT_NAME="vinova_cookie_preferences",
    )

    assert {"vinova_security.E013", "vinova_security.E014", "vinova_security.E015"}.issubset(ids)
