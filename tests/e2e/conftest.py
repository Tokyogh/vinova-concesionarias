"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Shared pytest fixtures for the e2e test suite.
"""

from __future__ import annotations

import os

import pytest


def pytest_collection_modifyitems(items):
    """Skip E2E tests during the regular Pytest suite.

    The dedicated runner sets VINOVA_E2E_ACTIVE=1 and executes these files with
    Playwright, a live Django server and an isolated test database.
    """

    if os.getenv("VINOVA_E2E_ACTIVE") == "1":
        return
    marker = pytest.mark.skip(reason="E2E se ejecuta solo mediante scripts/qa-e2e.* o el perfil full")
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(marker)
