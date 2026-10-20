"""ES: Este módulo especifica regresiones ejecutables para el dominio de calidad.

EN: This module specifies executable regressions for the quality domain.

Contexto existente / Existing context:
Regression coverage for e2e automation v0232 in the quality domain.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from types import SimpleNamespace
from pathlib import Path

import yaml
from django.conf import settings

from apps.quality.runner import _collect_e2e_evidence, _selected_steps


def _load_e2e_script():
    path = Path(settings.BASE_DIR) / "scripts" / "run_e2e.py"
    spec = importlib.util.spec_from_file_location("vinova_run_e2e", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_profiles_include_functional_browser_coverage():
    root = Path(settings.BASE_DIR)
    quick = {step.code for step in _selected_steps(root, "quick")}
    full = {step.code for step in _selected_steps(root, "full")}
    release = {step.code for step in _selected_steps(root, "release")}
    assert "e2e.chromium" not in quick
    assert "e2e.chromium" in full
    assert "e2e.cross_browser" in release
    assert full < release


def test_e2e_module_matrix_parser_reads_junit(tmp_path):
    module = _load_e2e_script()
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """<?xml version='1.0' encoding='utf-8'?>
        <testsuites><testsuite tests='2'>
          <testcase name='test_03_vehicle_creation_flow' time='1.5'/>
          <testcase name='test_05_inventory_item_and_stock_flow' time='2.0'><failure message='fallo'/></testcase>
        </testsuite></testsuites>""",
        encoding="utf-8",
    )
    results = module.parse_junit(junit, "chromium")
    assert results[0]["module"] == "Vehículos"
    assert results[0]["status"] == "passed"
    assert results[1]["module"] == "Inventario"
    assert results[1]["status"] == "failed"


def test_collect_e2e_evidence_aggregates_and_zips(tmp_path, monkeypatch):
    root = tmp_path / "project"
    report_dir = tmp_path / "reports"
    runtime = tmp_path / "runtime-outside-source"
    monkeypatch.setenv("VINOVA_QA_RUNTIME_ROOT", str(runtime))
    for relative, browser in (("e2e-full", "chromium"), ("e2e-release", "firefox")):
        directory = runtime / relative
        directory.mkdir(parents=True)
        (directory / "summary.json").write_text(
            json.dumps(
                {
                    "browsers": [browser],
                    "counts": {"passed": 1, "failed": 0, "skipped": 0},
                    "module_matrix": {
                        "Vehículos": {"passed": 1, "failed": 0, "error": 0, "skipped": 0, "total": 1}
                    },
                }
            ),
            encoding="utf-8",
        )
        (directory / f"{browser}.txt").write_text("evidencia", encoding="utf-8")

    summary, archive_name = _collect_e2e_evidence(root, report_dir, "abc123")
    assert summary["status"] == "passed"
    assert summary["browsers"] == ["chromium", "firefox"]
    assert summary["module_matrix"]["Vehículos"]["total"] == 2
    archive = report_dir / archive_name
    assert archive.is_file()
    with zipfile.ZipFile(archive) as package:
        assert any(name.endswith("chromium.txt") for name in package.namelist())


def test_e2e_script_accepts_absolute_writable_output(tmp_path, monkeypatch):
    module = _load_e2e_script()
    output = tmp_path / "runtime" / "e2e-full"

    def fake_run(command, cwd, env, check):
        junit = Path(command[command.index("--junitxml") + 1])
        junit.parent.mkdir(parents=True, exist_ok=True)
        junit.write_text(
            "<?xml version='1.0' encoding='utf-8'?><testsuites><testsuite tests='1'>"
            "<testcase name='test_03_vehicle_creation_flow' time='0.1'/></testsuite></testsuites>",
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(module, "browser_preflight", lambda browsers: ({"chromium": "/tmp/chromium"}, {}))
    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["run_e2e.py", "--browsers", "chromium", "--output", str(output)])
    assert module.main() == 0
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "passed"
    assert summary["counts"]["passed"] == 1


def test_qa_compose_uses_private_network_and_no_host_ports():
    compose = yaml.safe_load((Path(settings.BASE_DIR) / "docker-compose.qa.yml").read_text(encoding="utf-8"))
    assert compose["networks"]["qa_internal"]["internal"] is True
    for service_name in ("qa_db", "qa_redis"):
        service = compose["services"][service_name]
        assert service.get("ports") in (None, [])
        assert "qa_internal" in service["networks"]
    runner = compose["services"]["qa_runner"]
    assert runner["environment"]["VINOVA_QA_IGNORE_PROJECT_ENV"] == "True"
    assert "web" not in runner["depends_on"]
    assert "celery_worker" not in runner["depends_on"]


def test_powershell_hotfix_preserves_docker_diagnostics():
    script = (Path(settings.BASE_DIR) / "scripts" / "vinova-qa.ps1").read_text(encoding="utf-8")
    assert "docker info" in script
    assert "config --quiet" in script
    assert "logs --tail=120 qa_db qa_redis" in script
    assert "up -d --wait qa_db qa_redis" in script
    assert "up -d web celery_worker celery_beat qa_worker" not in script


def test_playwright_docker_image_is_pinned_non_root_and_has_python_runtime():
    dockerfile = (Path(settings.BASE_DIR) / "docker" / "qa" / "Dockerfile").read_text(encoding="utf-8")
    assert "mcr.microsoft.com/playwright:v1.60.0-noble" in dockerfile
    assert "python3 python3-venv" in dockerfile
    assert 'VIRTUAL_ENV=/opt/venv' in dockerfile
    assert 'python3 -m venv "${VIRTUAL_ENV}"' in dockerfile
    assert "QA Python runtime OK" in dockerfile
    assert "USER vinovaqa" in dockerfile
    assert "postgresql-client-16" in dockerfile


def test_windows_cmd_launcher_scopes_execution_policy_bypass():
    launcher = (Path(settings.BASE_DIR) / "scripts" / "vinova-qa.cmd").read_text(encoding="utf-8")
    assert "-ExecutionPolicy Bypass" in launcher
    assert "vinova-qa.ps1" in launcher
    assert "quick" in launcher and "full" in launcher and "release" in launcher


def test_product_version_is_v02325():
    assert settings.VINOVA_PRODUCT_VERSION == "2.0.0"
    assert settings.SPECTACULAR_SETTINGS["VERSION"] == settings.VINOVA_PRODUCT_VERSION


def test_e2e_suite_has_twelve_independent_business_scenarios():
    directory = Path(settings.BASE_DIR) / "tests" / "e2e"
    scenario_files = sorted(directory.glob("test_[0-9][0-9]_*.py"))
    assert len(scenario_files) == 12
    combined = "\n".join(path.read_text(encoding="utf-8") for path in scenario_files)
    for module_name in (
        "vehicle_creation_flow",
        "customer_creation_flow",
        "inventory_item_and_stock_flow",
        "crm_sales_and_invoice_flow",
        "role_and_permission_boundaries",
        "responsive_keyboard_and_accessibility_basics",
        "test_portal_responsive_keyboard_accessibility_and_module_gate",
        "test_12_generate_functional_maps",
    ):
        assert module_name in combined
