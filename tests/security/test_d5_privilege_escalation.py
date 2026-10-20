"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for d5 privilege escalation in the security domain.
"""

from __future__ import annotations

import re

import pytest
from django.urls import URLPattern, URLResolver, get_resolver

from apps.branches.models import Branch
from apps.companies.models import Company

EXCLUDED_PREFIXES = ("/admin/", "/health/", "/static/", "/media/")

CONVERTER_DEFAULTS = {
    "int": "1",
    "slug": "tmp",
    "str": "tmp",
    "uuid": "00000000-0000-0000-0000-000000000000",
    "path": "tmp/extra",
}

CONVERTER_PATTERN = re.compile(r"<(?P<name>[^:>]+):(?P<type>[a-z]+)>")

# Rutas que cualquier usuario autenticado debe poder abrir por sí mismo.
AUTHENTICATED_ALLOWLIST = {
    "/",
    "/accounts/profile/",
    "/dashboard/",
    "/security/password/change/",
    "/security/sessions/",
    "/security/2fa/setup/",
    "/security/2fa/disable/",
    "/security/2fa/backup-codes/",
    "/dashboard/help/",
    "/dashboard/help/search/",
    "/dashboard/help/training-mode/",
    # Vistas públicas (también accesibles sin sesión).
    "/leads/request/",
    "/privacy/cookies/",
    "/privacy/cookie-policy/",
    "/privacy/legal-notice/",
    "/privacy/policy/",
    "/privacy/request/",
    "/privacy/request/thanks/",
    "/privacy/terms/",
    "/vehicles/",
    "/repuestos/",
    "/instituciones/",
    "/servicios/",
    "/nosotros/",
    "/accounts/recuperar/",
    "/accounts/recuperar/<uidb64>/<token>/",
    "/accounts/recuperar/enviado/",
    "/accounts/recuperar/completo/",
    "/accounts/registro/revisa-tu-correo/",
    # Índice/metadatos de API: solo exponen nombres de rutas y versión.
    # Registrado como hallazgo INFO en la documentación maestra.
    "/api/",
    "/api/v1/",
    "/api/v1/meta/",
    # Reto 2FA accesible con sesión; sin secreto no permite avanzar. LOW.
    "/security/2fa/challenge/",
    # Estado propio de acceso adaptativo; no expone solicitudes ajenas ni concede permisos.
    "/security/staff-access/",
}


def _substitute(match: re.Match[str]) -> str:
    return CONVERTER_DEFAULTS.get(match.group("type"), "tmp")


def _reachable_paths():
    seen: set[str] = set()

    def walk(resolver, prefix):
        for entry in resolver.url_patterns:
            if isinstance(entry, URLResolver):
                yield from walk(entry, prefix + str(entry.pattern))
                continue
            if not isinstance(entry, URLPattern):
                continue
            path = prefix + str(entry.pattern)
            if not path or path.startswith(EXCLUDED_PREFIXES):
                continue
            path = CONVERTER_PATTERN.sub(_substitute, path)
            if path in seen:
                continue
            seen.add(path)
            yield path

    return sorted(walk(get_resolver(), "/"))


PATHS = _reachable_paths()


@pytest.fixture(name="staff_without_roles")
def staff_without_roles_fixture(django_user_model):
    # ES: force_login no necesita una contraseña utilizable en estas pruebas.
    # EN: force_login does not need a usable password in these tests.
    company = Company.objects.create(
        legal_name="Vinova Escalada S.A.",
        commercial_name="Vinova",
        ruc="1799999999003",
    )
    Branch.objects.create(company=company, name="Central", code="CT2", city="Quito")
    return django_user_model.objects.create_user(
        username="d5_no_roles", email="d5_no_roles@example.com", password=None
    )


@pytest.mark.django_db
@pytest.mark.parametrize("path", PATHS)
def test_staff_without_roles_cannot_open_internal_pages(client, staff_without_roles, path):
    client.force_login(staff_without_roles)

    response = client.get(path, follow=False)

    assert response.status_code < 500, f"{path} devolvió {response.status_code} sin roles"
    if response.status_code != 200:
        return

    unexpected = [path] if path not in AUTHENTICATED_ALLOWLIST else []
    assert not unexpected, (
        "Usuarios sin roles obtuvieron 200 en: "
        + ", ".join(sorted(unexpected))
    )
