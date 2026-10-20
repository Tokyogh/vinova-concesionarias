"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for assertions in the deployment_smoke helpers domain.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page


def select_first_nonempty(page: Page, name: str, *, required: bool = True) -> str:
    locator = page.locator(f"select[name='{name}']")
    if locator.count() == 0:
        if required:
            raise AssertionError(f"No existe el selector requerido {name!r}.")
        return ""
    values = locator.locator("option").evaluate_all(
        "options => options.map(option => ({value: option.value, disabled: option.disabled}))"
    )
    for option in values:
        value = str(option.get("value") or "")
        if value and not option.get("disabled"):
            locator.select_option(value)
            return value
    if required:
        raise AssertionError(f"El selector {name!r} no tiene opciones válidas.")
    return ""


def fill_if_present(page: Page, name: str, value: object) -> bool:
    locator = page.locator(f"[name='{name}']")
    if locator.count() == 0:
        return False
    locator.first.fill(str(value))
    return True


def select_value_if_present(page: Page, name: str, value: str) -> bool:
    locator = page.locator(f"select[name='{name}']")
    if locator.count() == 0:
        return False
    available = locator.locator(f"option[value='{value}']").count() > 0
    if available:
        locator.select_option(value)
    return available


def assert_no_overflow(page: Page) -> None:
    result = page.evaluate(
        """
        () => {
          const root = document.documentElement;
          const viewportWidth = root.clientWidth;
          const overflow = root.scrollWidth > viewportWidth + 2;
          const offenders = [...document.body.querySelectorAll('*')]
            .filter(el => {
              const style = getComputedStyle(el);
              if (style.display === 'none' || style.visibility === 'hidden') return false;
              const rect = el.getBoundingClientRect();
              return rect.width > 0 && (rect.right > viewportWidth + 2 || rect.left < -2);
            })
            .slice(0, 8)
            .map(el => {
              const rect = el.getBoundingClientRect();
              return {
                tag: el.tagName.toLowerCase(),
                id: el.id || '',
                classes: [...el.classList].slice(0, 4).join('.'),
                left: Math.round(rect.left),
                right: Math.round(rect.right),
                width: Math.round(rect.width),
                scrollWidth: el.scrollWidth,
                clientWidth: el.clientWidth,
              };
            });
          return {overflow, viewportWidth, scrollWidth: root.scrollWidth, offenders};
        }
        """
    )
    if result["overflow"]:
        offenders = ", ".join(
            f"{item['tag']}#{item['id']}.{item['classes']} "
            f"[{item['left']}..{item['right']}; w={item['width']}]"
            for item in result["offenders"]
        ) or "sin elemento identificado"
        raise AssertionError(
            "Se detectó overflow horizontal en "
            f"{page.url} (viewport={result['viewportWidth']}, scroll={result['scrollWidth']}). "
            f"Elementos: {offenders}."
        )


def unlabeled_controls(page: Page) -> list[str]:
    return page.evaluate(
        """
        () => [...document.querySelectorAll('input:not([type=hidden]), select, textarea')]
          .filter(el => {
            if (el.disabled) return false;
            const id = el.id;
            const explicit = id && document.querySelector(`label[for="${CSS.escape(id)}"]`);
            const wrapped = el.closest('label');
            const aria = el.getAttribute('aria-label') || el.getAttribute('aria-labelledby');
            return !explicit && !wrapped && !aria;
          })
          .map(el => el.name || el.id || el.tagName)
        """
    )
