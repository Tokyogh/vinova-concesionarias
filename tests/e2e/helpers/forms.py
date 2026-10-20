"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for forms in the e2e helpers domain.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from django.core.exceptions import ObjectDoesNotExist
from playwright.sync_api import Locator, Page, Response

T = TypeVar("T")


def submit_and_wait_for_url(
    page: Page,
    submitter: Locator,
    url_pattern,
    *,
    timeout: int = 45_000,
) -> Response:
    """Submit a form without racing the browser navigation.

    Calling ``wait_for_load_state`` after ``click`` can return immediately when
    the old document is already idle. WebKit may then still be sending the POST
    while the test starts querying Django. Pairing the click with
    ``expect_navigation`` removes that race and validates the real redirect.
    """

    with page.expect_navigation(wait_until="domcontentloaded", timeout=timeout) as navigation:
        submitter.click()

    response = navigation.value
    if response is None:
        raise AssertionError("El formulario no produjo una respuesta de navegación.")
    if response.status >= 400:
        raise AssertionError(f"El formulario respondió HTTP {response.status}: {response.url}")

    page.wait_for_url(url_pattern, wait_until="domcontentloaded", timeout=timeout)
    return response


def submit_form_and_wait_for_url(
    page: Page,
    form: Locator,
    url_pattern,
    *,
    timeout: int = 45_000,
) -> Response:
    """Submit a form element and wait atomically for its resulting navigation."""

    with page.expect_navigation(wait_until="domcontentloaded", timeout=timeout) as navigation:
        form.evaluate("element => element.submit()")

    response = navigation.value
    if response is None:
        raise AssertionError("El formulario no produjo una respuesta de navegación.")
    if response.status >= 400:
        raise AssertionError(f"El formulario respondió HTTP {response.status}: {response.url}")

    page.wait_for_url(url_pattern, wait_until="domcontentloaded", timeout=timeout)
    return response


def wait_for_database_object(
    getter: Callable[[], T],
    *,
    timeout_seconds: float = 10.0,
    description: str = "registro esperado",
) -> T:
    """Poll a deterministic ORM lookup until the completed request is visible."""

    deadline = time.monotonic() + timeout_seconds
    last_error: ObjectDoesNotExist | None = None
    while time.monotonic() < deadline:
        try:
            return getter()
        except ObjectDoesNotExist as exc:
            last_error = exc
            time.sleep(0.1)

    raise AssertionError(f"No apareció {description} en la base de datos tras {timeout_seconds:.1f} s.") from last_error
