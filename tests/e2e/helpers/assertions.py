"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for assertions in the e2e helpers domain.
"""

from __future__ import annotations

from playwright.sync_api import Page


def assert_no_document_overflow(page: Page, route: str, viewport: dict[str, int]) -> None:
    overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth + 2")
    offenders = page.evaluate(
        """
        () => {
          const viewportWidth = document.documentElement.clientWidth;
          return [...document.querySelectorAll('body *')]
            .map(element => {
              const rect = element.getBoundingClientRect();
              return {
                tag: element.tagName,
                id: element.id,
                className: typeof element.className === 'string' ? element.className : '',
                left: Math.round(rect.left),
                right: Math.round(rect.right),
                width: Math.round(rect.width),
              };
            })
            .filter(item => item.right > viewportWidth + 2 || item.left < -2)
            .slice(0, 12);
        }
        """
    )
    assert not overflow, f"Desbordamiento horizontal en {route} con {viewport}: {offenders}"


def assert_controls_are_labeled(page: Page, route: str) -> None:
    unlabeled = page.evaluate(
        """
        [...document.querySelectorAll('input:not([type=hidden]),select,textarea')]
          .filter(el => {
            if (el.getAttribute('aria-label') || el.getAttribute('aria-labelledby')) return false;
            if (el.id && document.querySelector(`label[for="${el.id}"]`)) return false;
            return !el.closest('label');
          })
          .map(el => ({
            tag: el.tagName,
            name: el.getAttribute('name') || '',
            id: el.id || '',
            type: el.getAttribute('type') || '',
          }));
        """
    )
    assert not unlabeled, f"Controles sin etiqueta en {route}: {unlabeled}"
