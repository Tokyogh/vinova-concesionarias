"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for deployment smoke inventory regression in the project domain.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_inventory_smoke_reselects_branch_after_redirect():
    source = (ROOT / "tests/deployment_smoke/test_write_flows.py").read_text(encoding="utf-8")

    first_selection = 'branch_value = select_first_nonempty(page, "branch")'
    second_selection = 'select_value_if_present(page, "branch", branch_value)'

    assert first_selection in source
    assert second_selection in source
    assert source.index(first_selection) < source.index(second_selection)


def test_submit_helper_reports_native_form_validation_before_waiting_navigation():
    source = (ROOT / "tests/deployment_smoke/helpers/forms.py").read_text(encoding="utf-8")

    assert "invalid_controls = form.evaluate" in source
    assert "El formulario no puede enviarse por validación del navegador" in source
    assert source.index("invalid_controls = form.evaluate") < source.index("page.expect_navigation")
