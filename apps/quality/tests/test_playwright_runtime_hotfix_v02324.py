"""ES: Este módulo especifica regresiones ejecutables para el dominio de calidad.

EN: This module specifies executable regressions for the quality domain.

Contexto existente / Existing context:
Regression coverage for playwright runtime hotfix v02324 in the quality domain.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import yaml
from django.conf import settings

from apps.quality.runner import _playwright_browsers_path, _safe_environment


def _load_e2e_script():
    path = Path(settings.BASE_DIR) / "scripts" / "run_e2e.py"
    spec = importlib.util.spec_from_file_location("vinova_run_e2e_v02324", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_safe_environment_preserves_trusted_playwright_browser_store(monkeypatch, tmp_path):
    browser_store = tmp_path / "ms-playwright"
    browser_store.mkdir()
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(browser_store))
    monkeypatch.setenv("VINOVA_QA_RUNTIME_ROOT", str(tmp_path / "runtime"))

    assert _playwright_browsers_path() == str(browser_store.resolve())
    environment = _safe_environment(Path(settings.BASE_DIR), profile="full")
    assert environment["PLAYWRIGHT_BROWSERS_PATH"] == str(browser_store.resolve())
    assert environment["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] == "1"
    assert environment["PLAYWRIGHT_BROWSERS_PATH"] != environment["XDG_CACHE_HOME"]


def test_safe_environment_rejects_relative_playwright_path(monkeypatch, tmp_path):
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", "relative/ms-playwright")
    monkeypatch.setenv("VINOVA_QA_PLAYWRIGHT_BROWSERS_PATH", "")
    monkeypatch.setenv("VINOVA_QA_RUNTIME_ROOT", str(tmp_path / "runtime"))
    assert _playwright_browsers_path() in {"", "/ms-playwright"}


def test_qa_composes_pin_official_playwright_browser_store():
    root = Path(settings.BASE_DIR)
    for filename in ("docker-compose.qa.yml", "docker-compose.qa-cli.yml"):
        compose = yaml.safe_load((root / filename).read_text(encoding="utf-8"))
        runner = compose["services"]["qa_runner"]
        assert runner["environment"]["VINOVA_QA_PLAYWRIGHT_BROWSERS_PATH"] == "/ms-playwright"
    enterprise = yaml.safe_load((root / "docker-compose.qa.yml").read_text(encoding="utf-8"))
    assert enterprise["services"]["qa_worker"]["environment"]["VINOVA_QA_PLAYWRIGHT_BROWSERS_PATH"] == "/ms-playwright"


def test_qa_dockerfile_verifies_all_three_browser_executables():
    dockerfile = (Path(settings.BASE_DIR) / "docker" / "qa" / "Dockerfile").read_text(encoding="utf-8")
    assert "PLAYWRIGHT_BROWSERS_PATH=/ms-playwright" in dockerfile
    assert "QA Playwright browsers OK" in dockerfile
    for browser in ("chromium", "firefox", "webkit"):
        assert browser in dockerfile


def test_e2e_preflight_reports_single_infrastructure_failure(tmp_path, monkeypatch):
    module = _load_e2e_script()
    output = tmp_path / "e2e"
    monkeypatch.setattr(module, "browser_preflight", lambda browsers: ({}, {"chromium": "/missing/chromium"}))
    monkeypatch.setattr(sys, "argv", ["run_e2e.py", "--browsers", "chromium", "--output", str(output)])

    assert module.main() == 1
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["counts"] == {"passed": 0, "failed": 1, "skipped": 0}
    assert list(summary["module_matrix"]) == ["Infraestructura E2E"]
    assert summary["results"][0]["test"] == "browser_preflight"


def test_e2e_runner_passes_resolved_executable_to_suite(tmp_path, monkeypatch):
    module = _load_e2e_script()
    output = tmp_path / "e2e"
    executable = tmp_path / "chromium"
    executable.write_text("browser", encoding="utf-8")
    monkeypatch.setattr(module, "browser_preflight", lambda browsers: ({"chromium": str(executable)}, {}))

    captured = {}

    def fake_run(command, cwd, env, check):
        captured["path"] = env["VINOVA_E2E_EXECUTABLE_PATH"]
        junit = Path(command[command.index("--junitxml") + 1])
        junit.parent.mkdir(parents=True, exist_ok=True)
        junit.write_text(
            "<?xml version='1.0' encoding='utf-8'?><testsuites><testsuite tests='1'>"
            "<testcase name='test_03_vehicle_creation_flow' time='0.1'/></testsuite></testsuites>",
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["run_e2e.py", "--browsers", "chromium", "--output", str(output)])
    assert module.main() == 0
    assert captured["path"] == str(executable)


def test_browser_preflight_accepts_explicit_single_browser_path(tmp_path, monkeypatch):
    module = _load_e2e_script()
    executable = tmp_path / "chromium"
    executable.write_text("browser", encoding="utf-8")
    monkeypatch.setenv("VINOVA_E2E_EXECUTABLE_PATH", str(executable))

    resolved, missing = module.browser_preflight(["chromium"])
    assert missing == {}
    assert resolved == {"chromium": str(executable.resolve())}
