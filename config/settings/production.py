"""ES: Este módulo implementa el componente production para el dominio de configuración.

EN: This module implements the production component for the configuration domain.

Contexto existente / Existing context:
Vinova runtime configuration for production.
"""

from __future__ import annotations

from .base import *  # noqa: F403

DEBUG = False
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_NAME = "__Host-vinova_session"
SESSION_COOKIE_PATH = "/"
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_NAME = "__Host-vinova_csrf"
CSRF_COOKIE_PATH = "/"
CSRF_COOKIE_DOMAIN = None
VINOVA_COOKIE_CONSENT_NAME = "__Host-vinova_cookie_preferences"
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)  # noqa: F405
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=True)  # noqa: F405
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if VINOVA_TRUST_PROXY_HEADERS else None  # noqa: F405
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE", default=28800)  # noqa: F405
SESSION_EXPIRE_AT_BROWSER_CLOSE = env.bool("SESSION_EXPIRE_AT_BROWSER_CLOSE", default=True)  # noqa: F405
SESSION_SAVE_EVERY_REQUEST = True
VINOVA_BACKUP_SYNC_FALLBACK = env.bool("VINOVA_BACKUP_SYNC_FALLBACK", default=False)  # noqa: F405
VINOVA_REQUIRE_CELERY_READY = env.bool("VINOVA_REQUIRE_CELERY_READY", default=True)  # noqa: F405
VINOVA_API_DOCS_PUBLIC = env.bool("VINOVA_API_DOCS_PUBLIC", default=False)  # noqa: F405

if not SECRET_KEY or SECRET_KEY.startswith("unsafe-"):  # noqa: F405
    raise RuntimeError("SECRET_KEY debe configurarse en producción")

VINOVA_API_TOKEN_PEPPER = env("VINOVA_API_TOKEN_PEPPER", default="")  # noqa: F405
if (
    len(VINOVA_API_TOKEN_PEPPER) < 32
    or VINOVA_API_TOKEN_PEPPER.startswith("change-me")
    or VINOVA_API_TOKEN_PEPPER == SECRET_KEY  # noqa: F405
):
    raise RuntimeError(
        "VINOVA_API_TOKEN_PEPPER debe ser un secreto aleatorio de al menos 32 caracteres "
        "y distinto de SECRET_KEY en producción"
    )
if VINOVA_WEBHOOK_ALLOW_PRIVATE_NETWORKS:  # noqa: F405
    raise RuntimeError("VINOVA_WEBHOOK_ALLOW_PRIVATE_NETWORKS debe ser False en producción")

SENTRY_DSN = env("SENTRY_DSN", default="")  # noqa: F405
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration(), RedisIntegration()],
        environment=env("SENTRY_ENVIRONMENT", default="production"),  # noqa: F405
        release=env("SENTRY_RELEASE", default=f"vinova-pro@{VINOVA_PRODUCT_VERSION}"),  # noqa: F405
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0),  # noqa: F405
        send_default_pii=False,
    )
