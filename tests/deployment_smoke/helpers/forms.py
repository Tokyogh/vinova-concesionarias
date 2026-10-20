"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for forms in the deployment_smoke helpers domain.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from playwright.sync_api import Page


def submit_and_wait(page: Page, button_name: str | re.Pattern[str] | None = None) -> str:
    button = (
        page.get_by_role("button", name=button_name)
        if button_name is not None
        else page.locator("form button[type='submit'], form button:not([type])").last
    )
    form = button.locator("xpath=ancestor::form[1]")
    if form.count() == 0:
        raise AssertionError("El botón de envío no pertenece a un formulario.")
    invalid_controls = form.evaluate(
        """
        form => [...form.elements]
          .filter(control => typeof control.checkValidity === 'function' && !control.checkValidity())
          .map(control => ({
            name: control.name || control.id || control.tagName.toLowerCase(),
            message: control.validationMessage || 'valor inválido',
          }))
        """
    )
    if invalid_controls:
        summary = ", ".join(
            f"{item['name']}: {item['message']}"
            for item in invalid_controls
        )
        raise AssertionError(f"El formulario no puede enviarse por validación del navegador: {summary}")
    with page.expect_navigation(wait_until="domcontentloaded"):
        button.click()
    return page.url


def path_from_url(url: str) -> str:
    return urlparse(url).path


def id_from_detail_url(url: str, prefix: str) -> int:
    match = re.search(re.escape(prefix.rstrip("/")) + r"/(\d+)/?$", path_from_url(url))
    if not match:
        raise AssertionError(f"No se pudo extraer el identificador de {url!r}.")
    return int(match.group(1))


def select_matching_vehicle_catalog(page: Page) -> tuple[str, str]:
    brand = page.locator("select[name='brand']")
    model = page.locator("select[name='model']")
    if brand.count() == 0 or model.count() == 0:
        raise AssertionError("El formulario de vehículo no contiene marca/modelo.")
    brands = brand.locator("option").evaluate_all(
        "opts => opts.map(o => ({value:o.value,text:(o.textContent||'').trim(),disabled:o.disabled})).filter(o => o.value && !o.disabled)"
    )
    models = model.locator("option").evaluate_all(
        "opts => opts.map(o => ({value:o.value,text:(o.textContent||'').trim(),disabled:o.disabled})).filter(o => o.value && !o.disabled)"
    )
    for brand_option in brands:
        brand_text = str(brand_option["text"]).strip().lower()
        for model_option in models:
            model_text = str(model_option["text"]).strip().lower()
            if brand_text and brand_text in model_text:
                brand.select_option(str(brand_option["value"]))
                model.select_option(str(model_option["value"]))
                return str(brand_option["value"]), str(model_option["value"])
    if brands and models:
        brand.select_option(str(brands[0]["value"]))
        model.select_option(str(models[0]["value"]))
        return str(brands[0]["value"]), str(models[0]["value"])
    raise AssertionError("Staging no tiene marcas y modelos activos para crear un vehículo de prueba.")
