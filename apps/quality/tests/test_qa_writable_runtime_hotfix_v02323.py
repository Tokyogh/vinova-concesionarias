"""ES: Este módulo especifica regresiones ejecutables para el dominio de calidad.

EN: This module specifies executable regressions for the quality domain.

Contexto existente / Existing context:
Regression coverage for qa writable runtime hotfix v02323 in the quality domain.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from django.conf import settings

from apps.quality.runner import _safe_environment, _selected_steps


def test_docker_context_keeps_required_production_example():
    dockerignore = (Path(settings.BASE_DIR) / ".dockerignore").read_text(encoding="utf-8")
    assert ".env.*" in dockerignore
    assert "!.env.example" in dockerignore
    assert "!.env.production.example" in dockerignore
    assert (Path(settings.BASE_DIR) / ".env.production.example").is_file()


def test_cli_compose_uses_writable_temporary_runtime_and_caches():
    compose = yaml.safe_load((Path(settings.BASE_DIR) / "docker-compose.qa-cli.yml").read_text(encoding="utf-8"))
    runner = compose["services"]["qa_runner"]
    environment = runner["environment"]
    assert environment["VINOVA_QA_RUNTIME_ROOT"].startswith("/tmp/")
    assert environment["RUFF_CACHE_DIR"].startswith("/tmp/")
    assert environment["XDG_CACHE_HOME"].startswith("/tmp/")
    assert "cache_dir=/tmp/" in environment["PYTEST_ADDOPTS"]
    assert all("/app/run/qa" not in str(item) for item in runner.get("tmpfs", []))


def test_enterprise_qa_services_use_writable_temporary_runtime():
    compose = yaml.safe_load((Path(settings.BASE_DIR) / "docker-compose.qa.yml").read_text(encoding="utf-8"))
    for service_name in ("qa_runner", "qa_worker"):
        service = compose["services"][service_name]
        environment = service["environment"]
        assert environment["VINOVA_QA_RUNTIME_ROOT"].startswith("/tmp/")
        assert environment["RUFF_CACHE_DIR"].startswith("/tmp/")
        assert "cache_dir=/tmp/" in environment["PYTEST_ADDOPTS"]
        assert all("/app/run/qa" not in str(volume) for volume in service.get("volumes", []))
    assert "scripts/vinova_qa.py" in compose["services"]["qa_runner"]["command"]


def test_runner_commands_follow_configured_runtime_root(monkeypatch, tmp_path):
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("VINOVA_QA_RUNTIME_ROOT", str(runtime))
    steps = {step.code: step for step in _selected_steps(Path(settings.BASE_DIR), "full")}
    assert str(runtime / "openapi.yaml") in steps["openapi.validate"].command
    assert str(runtime / "e2e-full") in steps["e2e.chromium"].command

    environment = _safe_environment(Path(settings.BASE_DIR), profile="full")
    assert environment["VINOVA_QA_RUNTIME_ROOT"] == str(runtime.resolve())
    assert environment["RUFF_CACHE_DIR"].startswith(str(runtime.resolve()))
    assert "cache_dir=" in environment["PYTEST_ADDOPTS"]


def test_qa_dockerfile_prepares_non_root_writable_runtime():
    dockerfile = (Path(settings.BASE_DIR) / "docker" / "qa" / "Dockerfile").read_text(encoding="utf-8")
    assert "/tmp/vinova-qa-runtime" in dockerfile
    assert "/tmp/vinova-qa-cache/ruff" in dockerfile
    assert "chown -R vinovaqa:vinovaqa" in dockerfile
    assert dockerfile.rstrip().endswith('CMD ["python", "manage.py", "run_quality_checks", "--profile", "quick"]')
