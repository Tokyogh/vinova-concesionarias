"""ES: Este módulo especifica regresiones ejecutables para el dominio de infraestructura compartida.

EN: This module specifies executable regressions for the common domain.

Contexto existente / Existing context:
Regression coverage for staging consolidation in the common domain.
"""

from __future__ import annotations

import os
import ssl
import sys
import urllib.request
from pathlib import Path

import pytest

from scripts import check_frontend_dependencies as frontend_dependencies
from scripts.normalize_shared_assets import DIRECTORY_MODE, FILE_MODE, normalize_tree
from tests.deployment_smoke.helpers import http


def test_http_request_installs_tls_context_for_http_redirect(monkeypatch):
    captured: list[object] = []

    class FakeOpener:
        def open(self, request, timeout):  # noqa: ANN001, ARG002
            raise RuntimeError("stop-after-opener")

    def fake_build_opener(*handlers):  # noqa: ANN001
        captured.extend(handlers)
        return FakeOpener()

    monkeypatch.setattr(urllib.request, "build_opener", fake_build_opener)

    try:
        http.request(
            "http://localhost/",
            timeout=1,
            follow_redirects=True,
            verify_tls=False,
        )
    except RuntimeError as exc:
        assert str(exc) == "stop-after-opener"

    https_handlers = [handler for handler in captured if isinstance(handler, urllib.request.HTTPSHandler)]
    assert len(https_handlers) == 1
    context = https_handlers[0]._context
    assert context.verify_mode == ssl.CERT_NONE
    assert context.check_hostname is False


@pytest.mark.skipif(sys.platform == "win32", reason="Permisos POSIX solo disponibles en Linux/Docker")
def test_normalize_shared_assets_sets_group_read_without_world_access(tmp_path: Path):
    root = tmp_path / "staticfiles"
    nested = root / "css"
    nested.mkdir(parents=True)
    asset = nested / "vinova.css"
    asset.write_text("body{}", encoding="utf-8")

    gid = os.getgid()
    directories, files = normalize_tree(root, gid)

    assert directories == 2
    assert files == 1
    assert root.stat().st_mode & 0o7777 == DIRECTORY_MODE
    assert nested.stat().st_mode & 0o7777 == DIRECTORY_MODE
    assert asset.stat().st_mode & 0o777 == FILE_MODE


def test_compose_runs_asset_normalization_with_shared_nginx_group():
    root = Path(__file__).resolve().parents[3]
    compose = (root / "docker-compose.prod.yml").read_text(encoding="utf-8")
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")

    assert '"${VINOVA_SHARED_ASSETS_GID:-101}"' in compose
    assert "python scripts/normalize_shared_assets.py" in compose
    assert "VINOVA_SHARED_ASSETS_GID=101" in dockerfile
    assert 'chown -R "${APP_UID}:101" /app/staticfiles /app/media' in dockerfile


def test_htmx_is_pinned_local_and_integrity_installer_is_versioned():
    root = Path(__file__).resolve().parents[3]
    base = (root / "templates/base/base.html").read_text(encoding="utf-8")
    public = (root / "templates/base/public.html").read_text(encoding="utf-8")
    installer = (root / "scripts/install_frontend_dependencies.ps1").read_text(encoding="utf-8")

    for template in (base, public):
        assert "vendor/htmx/htmx.min.js" in template
        assert "https://unpkg.com/htmx" not in template
    assert '$HtmxVersion = "2.0.10"' in installer
    assert "H5SrcfygHmAuTDZphMHqBJLc3FhssKjG7w/CeCpFReSfwBWDTKpkzPP8c+cLsK+V" in installer


def test_read_smoke_accepts_env_file_and_limits_insecure_tls_to_localhost():
    root = Path(__file__).resolve().parents[3]
    smoke = (root / "scripts/smoke-staging-read.ps1").read_text(encoding="utf-8")

    assert '[string]$EnvFile = ".env.staging"' in smoke
    assert 'Read-EnvValue -Key "VINOVA_SMOKE_BASE_URL"' in smoke
    assert '$Uri.Host -in @("localhost", "127.0.0.1", "::1")' in smoke
    assert '$Arguments += "--insecure-local-tls"' in smoke


def test_frontend_dependency_checker_rejects_missing_and_accepts_verified_file(tmp_path: Path, monkeypatch):
    missing = frontend_dependencies.validate(tmp_path)
    assert missing and "Falta HTMX local" in missing[0]

    htmx = tmp_path / frontend_dependencies.HTMX_RELATIVE_PATH
    htmx.parent.mkdir(parents=True)
    htmx.write_bytes(b"verified-test-build")
    monkeypatch.setattr(
        frontend_dependencies,
        "HTMX_SHA384_BASE64",
        frontend_dependencies.sha384_base64(htmx),
    )
    assert frontend_dependencies.validate(tmp_path) == []


def test_validate_staging_forwards_same_env_file_to_read_smoke():
    root = Path(__file__).resolve().parents[3]
    validate = (root / "scripts/validate-staging.ps1").read_text(encoding="utf-8")

    assert 'smoke-staging-read.ps1" -BaseUrl $BaseUrl -EnvFile $EnvFile' in validate


def test_staging_relaxes_only_nginx_login_rate_for_role_matrix():
    root = Path(__file__).resolve().parents[3]
    production = (root / "docker-compose.prod.yml").read_text(encoding="utf-8")
    staging = (root / "docker-compose.staging.yml").read_text(encoding="utf-8")
    https_template = (root / "docker/nginx/templates/https.conf.template").read_text(encoding="utf-8")
    http_template = (root / "docker/nginx/templates/http.conf.template").read_text(encoding="utf-8")

    assert "NGINX_LOGIN_RATE: ${NGINX_LOGIN_RATE:-10r/m}" in production
    assert "NGINX_LOGIN_BURST: ${NGINX_LOGIN_BURST:-10}" in production
    assert 'NGINX_LOGIN_RATE: "${NGINX_STAGING_LOGIN_RATE:-120r/m}"' in staging
    assert 'NGINX_LOGIN_BURST: "${NGINX_STAGING_LOGIN_BURST:-60}"' in staging
    for template in (https_template, http_template):
        assert "rate=${NGINX_LOGIN_RATE}" in template
        assert "burst=${NGINX_LOGIN_BURST}" in template
        assert "limit_req_status 429;" in template

    entrypoint = (root / "docker/nginx/entrypoint.sh").read_text(encoding="utf-8")
    assert "${NGINX_LOGIN_RATE} ${NGINX_LOGIN_BURST}" in entrypoint
    assert "configuracion Nginx contiene variables NGINX sin resolver" in entrypoint


def test_nginx_validator_replaces_login_rate_placeholders():
    from scripts.check_nginx_templates import render

    root = Path(__file__).resolve().parents[3]
    rendered = render(
        root / "docker/nginx/templates/http.conf.template",
        validator_version=(1, 30, 0),
    )

    assert "${NGINX_" not in rendered
    assert "rate=10r/m" in rendered
    assert "burst=10" in rendered


def test_gunicorn_disables_control_socket_on_read_only_runtime():
    root = Path(__file__).resolve().parents[3]
    config = (root / "config/gunicorn.conf.py").read_text(encoding="utf-8")

    assert "control_socket_disable" in config
    assert 'GUNICORN_CONTROL_SOCKET_DISABLE", "true"' in config


def test_staging_bot_rebuilds_images_when_revision_changes():
    root = Path(__file__).resolve().parents[3]
    runner = (root / "PROBAR-STAGING.ps1").read_text(encoding="utf-8")
    revision = (root / "scripts/staging-bot-revision.txt").read_text(encoding="utf-8").strip()

    assert revision == "20260717-r4"
    assert "/app/scripts/staging-bot-revision.txt" in runner
    assert "$EffectiveSkipBuild = $false" in runner
    assert "-SkipBuild:$EffectiveSkipBuild" in runner
