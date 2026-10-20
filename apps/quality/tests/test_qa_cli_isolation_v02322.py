"""ES: Este módulo especifica regresiones ejecutables para el dominio de calidad.

EN: This module specifies executable regressions for the quality domain.

Contexto existente / Existing context:
Regression coverage for qa cli isolation v02322 in the quality domain.
"""

from pathlib import Path

import yaml
from django.conf import settings


def test_cli_compose_is_standalone_and_does_not_load_company_environment():
    root = Path(settings.BASE_DIR)
    compose = yaml.safe_load((root / "docker-compose.qa-cli.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    assert set(services) == {"qa_db", "qa_redis", "qa_runner"}
    assert compose["networks"]["qa_internal"]["internal"] is True
    assert services["qa_db"].get("ports") in (None, [])
    assert services["qa_redis"].get("ports") in (None, [])
    runner = services["qa_runner"]
    assert "env_file" not in runner
    assert "scripts/vinova_qa.py" in runner["command"]
    assert "manage.py run_quality_checks" not in runner["command"]
    assert set(runner["depends_on"]) == {"qa_db", "qa_redis"}
    assert "qa_internal" in runner["networks"]
    assert runner["environment"]["VINOVA_QA_IGNORE_PROJECT_ENV"] == "True"
    assert all("docker.sock" not in str(volume) for volume in runner.get("volumes", []))


def test_console_scripts_use_dedicated_compose_project_and_standalone_runner():
    root = Path(settings.BASE_DIR)
    powershell = (root / "scripts" / "vinova-qa.ps1").read_text(encoding="utf-8-sig")
    shell = (root / "scripts" / "vinova-qa.sh").read_text(encoding="utf-8")
    for source in (powershell, shell):
        assert "docker-compose.qa-cli.yml" in source
        assert "vinova-qa-cli" in source
        assert "scripts/vinova_qa.py" in source
        assert "manage.py run_quality_checks" not in source
        assert "docker-compose.yml" not in source
    assert "OutputEncoding" in powershell
    assert "down --remove-orphans" in powershell
    assert "down --remove-orphans" in shell


def test_windows_launcher_enables_utf8_and_scopes_execution_policy():
    launcher = (Path(settings.BASE_DIR) / "scripts" / "vinova-qa.cmd").read_text(encoding="utf-8")
    assert "chcp 65001" in launcher
    assert "PYTHONUTF8=1" in launcher
    assert "-ExecutionPolicy Bypass" in launcher


def test_windows_qa_wrappers_keep_safe_preambles_without_embedded_bom():
    """ES: Evita que CMD o PowerShell interpreten cabeceras y parámetros como comandos.

    EN: Prevents CMD or PowerShell from interpreting headers and parameters as commands.
    """

    root = Path(settings.BASE_DIR) / "scripts"
    for name in ("qa-e2e.cmd", "qa-full.cmd", "qa-release.cmd", "vinova-qa.cmd"):
        data = (root / name).read_bytes()
        assert data.startswith(b"@echo off")
        assert data.splitlines()[1].isascii()
        assert data.splitlines()[2].isascii()
    for name in ("vinova-qa.ps1", "deploy-staging.ps1"):
        data = (root / name).read_bytes()
        assert b"\xef\xbb\xbf" not in data[3:]
        assert b"\nparam(" in data[:256]


def test_overlay_runner_is_also_standalone_but_worker_keeps_enterprise_history():
    compose = yaml.safe_load((Path(settings.BASE_DIR) / "docker-compose.qa.yml").read_text(encoding="utf-8"))
    assert "scripts/vinova_qa.py" in compose["services"]["qa_runner"]["command"]
    assert "env_file" not in compose["services"]["qa_runner"]
    assert compose["services"]["qa_worker"]["env_file"] == [".env"]
