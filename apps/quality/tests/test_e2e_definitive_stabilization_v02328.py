"""ES: Este módulo especifica regresiones ejecutables para el dominio de calidad.

EN: This module specifies executable regressions for the quality domain.

Contexto existente / Existing context:
Regression coverage for e2e definitive stabilization v02328 in the quality domain.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from django.conf import settings

from apps.customers.forms import CustomerSearchForm
from apps.inventory.forms import InventoryItemSearchForm
from apps.sales.forms import SaleSearchForm


def _read(relative: str) -> str:
    return (Path(settings.BASE_DIR) / relative).read_text(encoding="utf-8")


def test_inventory_e2e_uses_real_stock_relation():
    source = _read("tests/e2e/test_05_inventory.py")

    assert 'created.stock_records.get(branch=self.branch)' in source
    assert "created.branch_stocks" not in source


@pytest.mark.django_db
def test_all_responsive_list_filters_have_accessible_names():
    forms = (CustomerSearchForm(), SaleSearchForm(), InventoryItemSearchForm())

    for form in forms:
        for name, field in form.fields.items():
            assert field.widget.attrs.get("aria-label") == (field.label or name.replace("_", " ").title())
            assert "form-control" in field.widget.attrs.get("class", "")


def test_accessibility_e2e_reports_exact_unlabeled_controls():
    source = _read("tests/e2e/helpers/assertions.py")

    assert "name: el.getAttribute('name') || ''" in source
    assert 'assert not unlabeled, f"Controles sin etiqueta en {route}: {unlabeled}"' in source


def test_targeted_e2e_runner_has_closed_named_scenarios():
    source = _read("scripts/run_e2e.py")

    for scenario in ("public", "inventory", "accessibility", "portal"):
        assert f'"{scenario}": (' in source
    assert 'parser.add_argument("scenarios", nargs="*"' in source
    assert 'parser.add_argument("--fail-fast"' in source
    assert 'command.append("--maxfail=1")' in source
    assert '*(SCENARIOS[name][0] for name in selected)' in source


def test_targeted_e2e_runner_rejects_unknown_scenarios_and_writes_summary(tmp_path):
    output = tmp_path / "e2e"
    process = subprocess.run(
        [
            sys.executable,
            str(Path(settings.BASE_DIR) / "scripts/run_e2e.py"),
            "unknown-scenario",
            "--output",
            str(output),
        ],
        cwd=settings.BASE_DIR,
        text=True,
        capture_output=True,
        check=False,
    )

    assert process.returncode == 2
    assert "Escenarios E2E no permitidos" in process.stderr
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["phase"] == "argument-validation"


def test_targeted_platform_scripts_are_present_and_closed():
    cmd = _read("scripts/qa-e2e.cmd")
    powershell = _read("scripts/qa-e2e.ps1")
    shell = _read("scripts/qa-e2e.sh")

    assert "qa-e2e.ps1" in cmd
    assert "$AllowedScenarios" in powershell
    assert "No uses listas con comas" in powershell
    assert 'if ($Lower -eq "--rebuild")' in powershell
    assert 'switch ($Lower)' not in powershell
    assert '"python", "scripts/run_e2e.py"' in powershell
    assert "--fail-fast" in powershell
    assert "ALLOWED=" in shell
    assert 'scripts/run_e2e.py "${SCENARIOS[@]}"' in shell


def test_customer_dashboard_selectors_use_assigned_branch_contract():
    source = _read("apps/dashboard/selectors.py")

    assert 'customer_branch_filter = {"assigned_branch": branch}' in source
    assert 'select_related("assigned_branch", "assigned_advisor")' in source
    assert 'Customer.objects.filter(is_deleted=False).select_related("branch", "assigned_advisor")' not in source


def test_product_version_is_v02328():
    assert settings.VINOVA_PRODUCT_VERSION == "2.0.0"
    assert settings.SPECTACULAR_SETTINGS["VERSION"] == settings.VINOVA_PRODUCT_VERSION
