"""ES: Este módulo implementa el componente checks para el dominio de seguridad.

EN: This module implements the checks component for the security center domain.

Contexto existente / Existing context:
Django system checks for the security center domain.
"""

import os

from django.conf import settings
from django.core.checks import Error, Warning, register


@register("security")
def vinova_security_checks(app_configs, **kwargs):
    """Report unsafe runtime settings through Django's system-check framework."""

    issues = []
    settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "")
    production_mode = settings_module.endswith(".production")
    if production_mode and str(settings.SECRET_KEY).startswith("unsafe-"):
        issues.append(Error("SECRET_KEY insegura en producción.", id="vinova_security.E001"))
    if production_mode and not getattr(settings, "SESSION_COOKIE_SECURE", False):
        issues.append(Error("SESSION_COOKIE_SECURE debe estar activo.", id="vinova_security.E002"))
    if production_mode and not getattr(settings, "CSRF_COOKIE_SECURE", False):
        issues.append(Error("CSRF_COOKIE_SECURE debe estar activo.", id="vinova_security.E003"))
    if production_mode and getattr(settings, "DEBUG", False):
        issues.append(Error("DEBUG debe estar desactivado en producción.", id="vinova_security.E004"))
    if production_mode and not getattr(settings, "SECURE_SSL_REDIRECT", False):
        issues.append(Error("SECURE_SSL_REDIRECT debe estar activo.", id="vinova_security.E005"))
    if production_mode and int(getattr(settings, "SECURE_HSTS_SECONDS", 0) or 0) <= 0:
        issues.append(Error("SECURE_HSTS_SECONDS debe ser mayor que cero.", id="vinova_security.E006"))
    allowed_hosts = set(getattr(settings, "ALLOWED_HOSTS", []))
    if production_mode and (not allowed_hosts or "*" in allowed_hosts):
        issues.append(Error("ALLOWED_HOSTS debe ser una lista explícita.", id="vinova_security.E007"))
    trusted_origins = tuple(getattr(settings, "CSRF_TRUSTED_ORIGINS", ()))
    if production_mode and (not trusted_origins or any(not origin.startswith("https://") for origin in trusted_origins)):
        issues.append(Error("CSRF_TRUSTED_ORIGINS debe usar orígenes HTTPS explícitos.", id="vinova_security.E008"))
    if production_mode and not getattr(settings, "SESSION_COOKIE_HTTPONLY", False):
        issues.append(Error("SESSION_COOKIE_HTTPONLY debe estar activo.", id="vinova_security.E009"))
    if production_mode and getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False):
        issues.append(Error("CORS_ALLOW_ALL_ORIGINS no puede estar activo.", id="vinova_security.E010"))
    middleware = set(getattr(settings, "MIDDLEWARE", ()))
    if production_mode and "django.middleware.csrf.CsrfViewMiddleware" not in middleware:
        issues.append(Error("CsrfViewMiddleware es obligatorio.", id="vinova_security.E011"))
    if production_mode and "apps.security_center.middleware.SecurityHeadersMiddleware" not in middleware:
        issues.append(Error("SecurityHeadersMiddleware es obligatorio.", id="vinova_security.E012"))
    if production_mode and not (
        str(getattr(settings, "SESSION_COOKIE_NAME", "")).startswith("__Host-")
        and getattr(settings, "SESSION_COOKIE_PATH", None) == "/"
        and not getattr(settings, "SESSION_COOKIE_DOMAIN", None)
    ):
        issues.append(Error("La cookie de sesión debe cumplir el prefijo __Host-.", id="vinova_security.E013"))
    if production_mode and not (
        str(getattr(settings, "CSRF_COOKIE_NAME", "")).startswith("__Host-")
        and getattr(settings, "CSRF_COOKIE_PATH", None) == "/"
        and not getattr(settings, "CSRF_COOKIE_DOMAIN", None)
    ):
        issues.append(Error("La cookie CSRF debe cumplir el prefijo __Host-.", id="vinova_security.E014"))
    if production_mode and not str(getattr(settings, "VINOVA_COOKIE_CONSENT_NAME", "")).startswith("__Host-"):
        issues.append(
            Error(
                "La cookie de preferencias debe cumplir el prefijo __Host-.",
                id="vinova_security.E015",
            )
        )
    if not getattr(settings, "SECURE_CONTENT_TYPE_NOSNIFF", False):
        issues.append(Warning("SECURE_CONTENT_TYPE_NOSNIFF no está activo.", id="vinova_security.W001"))
    return issues
