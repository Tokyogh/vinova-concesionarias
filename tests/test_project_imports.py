"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for project imports in the project domain.
"""

def test_settings_imports():
    import config.settings.local  # noqa
