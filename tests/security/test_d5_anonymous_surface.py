"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for d5 anonymous surface in the security domain.
"""

from __future__ import annotations

import re

import pytest
from django.urls import URLPattern, URLResolver, get_resolver

EXCLUDED_PREFIXES = ("/admin/", "/health/", "/static/", "/media/")

CONVERTER_DEFAULTS = {
    "int": "1",
    "slug": "tmp",
    "str": "tmp",
    "uuid": "00000000-0000-0000-0000-000000000000",
    "path": "tmp/extra",
}

CONVERTER_PATTERN = re.compile(r"<(?P<name>[^:>]+):(?P<type>[a-z]+)>")


def _substitute(match: re.Match[str]) -> str:
    return CONVERTER_DEFAULTS.get(match.group("type"), "tmp")


def _anonymous_reachable_paths():
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


PATHS = _anonymous_reachable_paths()


@pytest.mark.django_db
@pytest.mark.parametrize("path", PATHS)
def test_no_route_crashes_for_anonymous_visitors(client, path):
    response = client.get(path, follow=False)

    assert response.status_code < 500, f"{path} devolvió {response.status_code} para un visitante anónimo"
