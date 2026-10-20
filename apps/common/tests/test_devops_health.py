"""ES: Este módulo especifica regresiones ejecutables para el dominio de infraestructura compartida.

EN: This module specifies executable regressions for the common domain.

Contexto existente / Existing context:
Regression coverage for devops health in the common domain.
"""

from __future__ import annotations

import time
from io import StringIO
from pathlib import Path

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.test import override_settings
from django.urls import resolve, reverse

from apps.common.checks import vinova_operational_checks
from apps.common.tasks import system_heartbeat
from apps.continuity.tasks import run_backup_task, schedule_policy_backups  # noqa: F401  (registro de tasks en el app de celery)
from config import celery_app


pytestmark = pytest.mark.django_db


def test_celery_application_uses_django_broker(settings):
    assert celery_app.conf.broker_url == settings.CELERY_BROKER_URL
    assert celery_app.conf.result_backend == settings.CELERY_RESULT_BACKEND
    assert "apps.continuity.tasks.run_backup_task" in celery_app.tasks
    assert "apps.continuity.tasks.schedule_policy_backups" in celery_app.tasks


def test_operational_check_rejects_disabled_resource_limits(settings):
    settings.VINOVA_IMPORT_MAX_ROWS = 0

    issues = vinova_operational_checks(None)

    assert any(issue.id == "vinova.E004" and "VINOVA_IMPORT_MAX_ROWS" in issue.msg for issue in issues)


def test_health_routes_resolve():
    assert resolve("/health/live/").url_name == "health-live"
    assert reverse("health-ready") == "/health/ready/"


def test_liveness_is_public_and_minimal(client):
    response = client.get("/health/live/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "vinova-pro"}


def test_readiness_checks_database_cache_and_storage(client, tmp_path):
    with override_settings(
        PRIVATE_STORAGE_ROOT=tmp_path / "private",
        PRIVATE_STORAGE_BACKEND="local",
        VINOVA_REQUIRE_CELERY_READY=False,
    ):
        response = client.get("/health/ready/")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_fails_without_celery_heartbeat_when_required(client, tmp_path):
    cache.delete("vinova:test:celery-health")
    with override_settings(
        PRIVATE_STORAGE_ROOT=tmp_path / "private",
        PRIVATE_STORAGE_BACKEND="local",
        VINOVA_REQUIRE_CELERY_READY=True,
        VINOVA_CELERY_HEALTH_KEY="vinova:test:celery-health",
        VINOVA_CELERY_HEARTBEAT_MAX_AGE=60,
    ):
        response = client.get("/health/ready/")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


def test_celery_heartbeat_makes_pipeline_ready(client, tmp_path):
    key = "vinova:test:celery-health-ready"
    with override_settings(
        PRIVATE_STORAGE_ROOT=tmp_path / "private",
        PRIVATE_STORAGE_BACKEND="local",
        VINOVA_REQUIRE_CELERY_READY=True,
        VINOVA_CELERY_HEALTH_KEY=key,
        VINOVA_CELERY_HEARTBEAT_MAX_AGE=60,
    ):
        started_at = time.time()
        payload = system_heartbeat()
        finished_at = time.time()
        assert started_at - 0.01 <= payload["timestamp"] <= finished_at + 0.01
        response = client.get("/health/ready/")
    assert response.status_code == 200


def test_dependency_details_require_staff(client, django_user_model, tmp_path):
    response = client.get("/health/dependencies/")
    assert response.status_code == 302

    staff = django_user_model.objects.create_user(
        username="ops-staff",
        email="ops@example.com",
        password="test12345",
        is_staff=True,
    )
    client.force_login(staff)
    with override_settings(
        PRIVATE_STORAGE_ROOT=Path(tmp_path) / "private",
        PRIVATE_STORAGE_BACKEND="local",
        VINOVA_REQUIRE_CELERY_READY=False,
    ):
        response = client.get("/health/dependencies/")
    assert response.status_code == 200
    assert response.json()["checks"]["database"]["ok"] is True


def test_api_documentation_is_protected_in_test_settings(client, django_user_model):
    anonymous = client.get("/api/schema/")
    assert anonymous.status_code in {401, 403}

    staff = django_user_model.objects.create_superuser(
        username="schema-admin",
        email="schema@example.com",
        password="test12345",
    )
    client.force_login(staff)
    response = client.get("/api/schema/")
    assert response.status_code == 200


def test_internal_health_probe_uses_trusted_https_header(client):
    with override_settings(
        SECURE_SSL_REDIRECT=True,
        SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
    ):
        redirected = client.get("/health/live/")
        ready = client.get("/health/live/", HTTP_X_FORWARDED_PROTO="https")
    assert redirected.status_code == 301
    assert ready.status_code == 200


def test_external_private_storage_failure_makes_readiness_unavailable(client, settings, monkeypatch):
    settings.PRIVATE_STORAGE_BACKEND = "s3"
    settings.STORAGE_BACKEND = "local"
    settings.VINOVA_REQUIRE_CELERY_READY = False
    monkeypatch.setattr(
        "apps.documents.storage.private_storage_health_check",
        lambda: (False, "ProviderUnavailable"),
    )

    response = client.get("/health/ready/")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


def test_cloudinary_failure_makes_readiness_unavailable(client, settings, monkeypatch, tmp_path):
    settings.PRIVATE_STORAGE_BACKEND = "local"
    settings.PRIVATE_STORAGE_ROOT = tmp_path / "private"
    settings.STORAGE_BACKEND = "cloudinary"
    settings.VINOVA_REQUIRE_CELERY_READY = False
    monkeypatch.setattr(
        "apps.accounts.storage.avatar_storage_health_check",
        lambda: (False, "ProviderUnavailable"),
    )

    response = client.get("/health/ready/")

    assert response.status_code == 503


def test_storage_smoke_command_runs_full_local_lifecycle(settings, tmp_path):
    settings.STORAGE_BACKEND = "local"
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.PRIVATE_STORAGE_BACKEND = "local"
    settings.PRIVATE_STORAGE_ROOT = tmp_path / "private"
    output = StringIO()

    call_command("check_storage_integrations", live=True, stdout=output)

    assert "Ciclos live" in output.getvalue()
    assert list((tmp_path / "media").rglob("*.png")) == []
    assert list((tmp_path / "private").rglob("*.txt")) == []
