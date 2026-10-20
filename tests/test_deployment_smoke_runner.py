"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for deployment smoke runner in the project domain.
"""

from __future__ import annotations

import json
import pytest

from scripts import run_deployment_smoke as runner
from tests.deployment_smoke.helpers.models import CheckResult, RunState, SmokeConfig
from tests.deployment_smoke.helpers.security import redact


def test_closed_scenario_contract_rejects_commas():
    with pytest.raises(ValueError, match="comas"):
        runner.normalize_scenarios(["auth,health"], "production")


def test_production_rejects_write_mode(monkeypatch):
    monkeypatch.delenv("VINOVA_SMOKE_ALLOW_WRITE", raising=False)
    args = runner.build_parser().parse_args(
        ["https://example.com", "--mode", "production", "--write-tests", "--scenario", "customers"]
    )
    with pytest.raises(runner.ConfigurationError, match="Producción"):
        runner.validate_config(args)


def test_staging_requires_environment_write_authorization(monkeypatch):
    monkeypatch.delenv("VINOVA_SMOKE_ALLOW_WRITE", raising=False)
    args = runner.build_parser().parse_args(
        [
            "https://staging.example.com",
            "--mode",
            "staging",
            "--write-tests",
            "--cleanup",
            "--scenario",
            "customers",
            "--username",
            "smoke",
            "--password",
            "secret",
        ]
    )
    with pytest.raises(runner.ConfigurationError, match="VINOVA_SMOKE_ALLOW_WRITE"):
        runner.validate_config(args)


def test_report_is_generated_for_invalid_arguments(tmp_path, monkeypatch):
    monkeypatch.setenv("VINOVA_SMOKE_REPORT_DIR", str(tmp_path))
    exit_code = runner.main(["not-a-url"])
    assert exit_code == 2
    summaries = list(tmp_path.glob("deployment-smoke-*/summary.json"))
    assert len(summaries) == 1
    payload = json.loads(summaries[0].read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert payload["exit_code"] == 2


def test_summary_contract_and_redaction(tmp_path):
    config = SmokeConfig(
        base_url="https://example.com",
        mode="production",
        scenarios=["tls"],
        report_root=tmp_path,
        run_id="abcdef123456",
    )
    state = RunState(config=config, output_dir=tmp_path / "result")
    state.add(CheckResult(code="tls.ok", scenario="tls", title="TLS", status="passed", message="ok"))
    summary = state.write_summary()
    payload = json.loads(summary.read_text(encoding="utf-8"))
    assert payload["source_version"] == "2.0.0"
    assert payload["deployment_ready"] is True
    assert redact("password=supersecret", ["supersecret"]) == "password=[REDACTED]"


def test_missing_browser_dependency_generates_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("VINOVA_SMOKE_REPORT_DIR", str(tmp_path))

    def fail_enter(self):  # noqa: ANN001
        raise runner.BrowserDependencyError("Navegador Playwright no instalado")

    monkeypatch.setattr(runner.BrowserSession, "__enter__", fail_enter)
    exit_code = runner.main(["https://example.com", "--scenario", "public"])

    assert exit_code == 3
    summaries = list(tmp_path.rglob("summary.json"))
    assert len(summaries) == 1
    payload = json.loads(summaries[0].read_text(encoding="utf-8"))
    assert payload["exit_code"] == 3
    assert payload["checks"][0]["code"] == "runner.dependencies"


def test_roles_scenario_accepts_manifest_without_primary_credentials(tmp_path):
    manifest = tmp_path / "roles.json"
    manifest.write_text("{}", encoding="utf-8")
    args = runner.build_parser().parse_args(
        [
            "http://127.0.0.1:8000",
            "--allow-http-local",
            "--scenario",
            "roles",
            "--role-credentials-file",
            str(manifest),
        ]
    )
    config = runner.validate_config(args)
    assert config.scenarios == ["roles"]
    assert config.role_credentials_file == manifest.resolve()


def test_roles_scenario_requires_manifest():
    args = runner.build_parser().parse_args(
        ["http://127.0.0.1:8000", "--allow-http-local", "--scenario", "roles"]
    )
    with pytest.raises(runner.ConfigurationError, match="role-credentials-file"):
        runner.validate_config(args)


def test_role_response_classification():
    from tests.deployment_smoke.test_roles import _is_allowed_response

    assert _is_allowed_response(200, "") is True
    assert _is_allowed_response(302, "/dashboard/") is True
    assert _is_allowed_response(302, "/accounts/profile/") is False
    assert _is_allowed_response(403, "") is False


class _CookieContext:
    def __init__(self, cookies):
        self._cookies = cookies

    def cookies(self):
        return self._cookies


class _CookieSession:
    def __init__(self, cookies):
        self.context = _CookieContext(cookies)


def _local_http_cookies():
    return [
        {"name": "csrftoken", "secure": False, "httpOnly": False, "sameSite": "Lax"},
        {"name": "sessionid", "secure": False, "httpOnly": True, "sameSite": "Lax"},
    ]


def test_cookie_security_is_warning_for_explicit_local_http():
    from tests.deployment_smoke.test_security import _cookies

    result = _cookies(_CookieSession(_local_http_cookies()), "production", allow_http_local=True)
    assert result["status"] == "warning"
    assert result["insecure_local_cookies"] == ["csrftoken", "sessionid"]


def test_cookie_security_remains_required_for_real_production():
    from tests.deployment_smoke.test_security import _cookies

    with pytest.raises(AssertionError, match="sin Secure"):
        _cookies(_CookieSession(_local_http_cookies()), "production", allow_http_local=False)


def test_local_staging_can_explicitly_skip_ca_verification():
    args = runner.build_parser().parse_args(
        [
            "https://localhost",
            "--mode",
            "staging",
            "--scenario",
            "tls",
            "--insecure-local-tls",
        ]
    )
    config = runner.validate_config(args)
    assert config.verify_tls is False


def test_production_rejects_insecure_local_tls():
    args = runner.build_parser().parse_args(
        ["https://localhost", "--mode", "production", "--scenario", "tls", "--insecure-local-tls"]
    )
    with pytest.raises(runner.ConfigurationError, match="Producción"):
        runner.validate_config(args)


def test_nonlocal_staging_rejects_insecure_tls():
    args = runner.build_parser().parse_args(
        [
            "https://staging.example.com",
            "--mode",
            "staging",
            "--scenario",
            "tls",
            "--insecure-local-tls",
        ]
    )
    with pytest.raises(runner.ConfigurationError, match="localhost"):
        runner.validate_config(args)
