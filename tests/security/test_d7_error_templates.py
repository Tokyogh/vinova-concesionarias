# -*- coding: utf-8 -*-
"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
D7 — plantillas de error de producto (403/404/500).

Cierra el hallazgo D6: antes Django servía sus páginas por defecto sin tema
Light/Dark (data-theme=None), sin identidad de producto ni navegación.
Verifica que las nuevas plantillas se renderizan, no filtran el código de
estado como texto y cargan theme.js para mantener el tema del producto.
"""
from __future__ import annotations

import pytest
from django.views import defaults as django_defaults
from django.test import RequestFactory

LEAK_TOKENS = ("Traceback", "SECRET", "db_name", "django.db")


@pytest.mark.django_db
def test_custom_404_page_is_branded_and_theme_aware(client):
    response = client.get("/ruta-que-no-existe-d7/")

    assert response.status_code == 404
    body = response.content.decode()
    assert "Página no encontrada" in body
    assert "js/theme.js" in body
    assert "errors.css" in body
    assert "Volver al inicio" in body
    for token in (*LEAK_TOKENS, "404", "500"):
        assert token not in body, f"la página 404 filtró '{token}'"


@pytest.mark.django_db
def test_custom_403_page_is_branded_and_theme_aware():
    request = RequestFactory().get("/seccion-protegida")
    response = django_defaults.permission_denied(request, exception=None)

    assert response.status_code == 403
    body = response.content.decode()
    assert "Acceso denegado" in body
    assert "js/theme.js" in body
    assert "errors.css" in body
    for token in (*LEAK_TOKENS, "403", "404", "500"):
        assert token not in body, f"la página 403 filtró '{token}'"


@pytest.mark.django_db
def test_custom_500_page_is_branded_and_theme_aware():
    request = RequestFactory().get("/boom")
    response = django_defaults.server_error(request)

    assert response.status_code == 500
    body = response.content.decode()
    assert "Error interno del servidor" in body
    assert "js/theme.js" in body
    assert "errors.css" in body
    for token in (*LEAK_TOKENS, "403", "404", "500"):
        assert token not in body, f"la página 500 filtró '{token}'"


@pytest.mark.django_db
def test_error_pages_render_without_duplicate_doctypes(client):
    body = client.get("/ruta-que-no-existe-d7/").content.decode()
    assert body.strip().lower().startswith("<!doctype html>")
    assert body.count("<!doctype html>") == 1