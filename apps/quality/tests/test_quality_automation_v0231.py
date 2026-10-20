"""ES: Este módulo especifica regresiones ejecutables para el dominio de calidad.

EN: This module specifies executable regressions for the quality domain.

Contexto existente / Existing context:
Regression coverage for quality automation v0231 in the quality domain.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import resolve, reverse
from django.utils import timezone

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.quality.models import QualityCheckResult, QualityRun
from apps.quality.permissions import can_run_quality, can_view_quality
from apps.quality.runner import _safe_environment, _selected_steps, redact
from apps.quality.services import (
    _safe_report_relative_path,
    apply_quality_report,
    QUALITY_RUN_CREATE_LOCK_KEY,
    cleanup_expired_quality_evidence,
    create_quality_run,
    expire_stale_quality_runs,
)


@pytest.fixture
def quality_user(django_user_model):
    user = django_user_model.objects.create_user(
        username="quality-auditor",
        email="quality-auditor@example.com",
        password="safe-test-password",
    )
    permission = PermissionCode.objects.create(module="quality", code="quality.view", name="Ver QA")
    role = Role.objects.create(code="quality-auditor", name="Auditor QA", level=10)
    role.permissions.add(permission)
    UserRole.objects.create(user=user, role=role, is_active=True)
    return user


@pytest.mark.django_db
def test_quality_permissions_and_panel_are_backend_enforced(client, django_user_model, quality_user):
    outsider = django_user_model.objects.create_user(
        username="quality-outsider",
        email="quality-outsider@example.com",
        password="safe-test-password",
    )
    client.force_login(outsider)
    assert client.get(reverse("quality:run_list")).status_code == 403

    client.force_login(quality_user)
    response = client.get(reverse("quality:run_list"))
    assert response.status_code == 200
    assert can_view_quality(quality_user)
    assert not can_run_quality(quality_user)
    assert "QA Bot empresarial" in response.content.decode()


@pytest.mark.django_db
def test_only_run_permission_can_start_profile(client, django_user_model, monkeypatch):
    user = django_user_model.objects.create_user(
        username="quality-runner",
        email="quality-runner@example.com",
        password="safe-test-password",
    )
    permission = PermissionCode.objects.create(module="quality", code="quality.run", name="Ejecutar QA")
    role = Role.objects.create(code="quality-runner", name="Operador QA", level=5)
    role.permissions.add(permission)
    UserRole.objects.create(user=user, role=role, is_active=True)
    monkeypatch.setattr(
        "apps.quality.views.enqueue_quality_run",
        lambda run: SimpleNamespace(run=run, queued=True, message="En cola"),
    )
    client.force_login(user)
    response = client.post(reverse("quality:run_create"), {"profile": QualityRun.Profile.QUICK})
    run = QualityRun.objects.get()
    assert response.status_code == 302
    assert response.headers["Location"] == reverse("quality:run_detail", kwargs={"public_id": run.public_id})
    assert run.requested_by == user
    assert run.trigger == QualityRun.Trigger.PANEL


@pytest.mark.django_db
def test_branch_scoped_quality_permissions_cannot_access_global_qa(client, django_user_model):
    company = Company.objects.create(
        legal_name="QA Company SA", commercial_name="QA Company", ruc="1790012345001"
    )
    branch = Branch.objects.create(company=company, name="Principal", code="QA-BRANCH", city="Quito")
    user = django_user_model.objects.create_user(
        username="branch-quality-runner",
        email="branch-quality-runner@example.com",
        password="safe-test-password",
    )
    view_permission = PermissionCode.objects.create(module="quality", code="quality.view", name="Ver QA")
    run_permission = PermissionCode.objects.create(module="quality", code="quality.run", name="Ejecutar QA")
    role = Role.objects.create(code="branch-quality-runner", name="Operador QA sucursal", level=5)
    role.permissions.add(view_permission, run_permission)
    UserRole.objects.create(user=user, role=role, branch=branch, is_active=True)

    client.force_login(user)
    assert not can_view_quality(user)
    assert not can_run_quality(user)
    assert client.get(reverse("quality:run_list")).status_code == 403
    assert client.post(reverse("quality:run_create"), {"profile": QualityRun.Profile.QUICK}).status_code == 403
    assert client.get(reverse("api_v1:quality-api:run_list")).status_code == 403
    assert (
        client.post(
            reverse("api_v1:quality-api:run_create"),
            {"profile": QualityRun.Profile.QUICK},
            content_type="application/json",
        ).status_code
        == 403
    )


@pytest.mark.django_db
def test_quality_internal_api_is_session_only_and_uses_closed_profiles(client, django_user_model, monkeypatch):
    user = django_user_model.objects.create_superuser(
        username="qa-superadmin",
        email="qa-superadmin@example.com",
        password="safe-test-password",
    )
    monkeypatch.setattr(
        "apps.quality.api.views.enqueue_quality_run",
        lambda run: SimpleNamespace(run=run, queued=True, message="En cola"),
    )
    client.force_login(user)
    endpoint = reverse("api_v1:quality-api:run_create")
    invalid = client.post(endpoint, {"profile": "custom-command"}, content_type="application/json")
    assert invalid.status_code == 400
    accepted = client.post(endpoint, {"profile": "quick"}, content_type="application/json")
    assert accepted.status_code == 202
    assert accepted.json()["queued"] is True


@pytest.mark.django_db
def test_quality_run_concurrency_is_limited(settings):
    settings.VINOVA_QA_MAX_CONCURRENT_RUNS = 1
    create_quality_run(profile="quick", trigger=QualityRun.Trigger.CLI)
    with pytest.raises(ValueError, match="Ya existe"):
        create_quality_run(profile="full", trigger=QualityRun.Trigger.CLI)


@pytest.mark.django_db
def test_quality_report_is_persisted_without_public_paths(tmp_path, settings):
    settings.VINOVA_QA_REPORT_ROOT = tmp_path
    run = QualityRun.objects.create(profile="quick", trigger=QualityRun.Trigger.CLI, status=QualityRun.Status.RUNNING)
    json_path = tmp_path / f"qa-{run.public_id}.json"
    html_path = tmp_path / f"qa-{run.public_id}.html"
    json_path.write_text("{}", encoding="utf-8")
    html_path.write_text("<html></html>", encoding="utf-8")
    report = {
        "schema_version": 1,
        "run_id": str(run.public_id),
        "status": "passed",
        "release_ready": False,
        "source_version": settings.VINOVA_PRODUCT_VERSION,
        "source_commit": "abc123",
        "environment": "test",
        "duration_seconds": 1.25,
        "counts": {"passed": 1, "warning": 0, "failed": 0, "skipped": 0},
        "database": {"engine": "sqlite", "isolated": False},
        "checks": [
            {
                "code": "django.check",
                "category": "Django",
                "title": "Django check",
                "status": "passed",
                "duration_seconds": 1.0,
                "command": ["python", "manage.py", "check"],
                "message": "OK",
                "output": "System check identified no issues",
            }
        ],
        "report_json_path": str(json_path),
        "report_html_path": str(html_path),
    }
    updated = apply_quality_report(run, report)
    assert updated.status == QualityRun.Status.PASSED
    assert updated.report_json_path == json_path.name
    assert updated.report_html_path == html_path.name
    assert updated.checks.get().status == QualityCheckResult.Status.PASSED


@pytest.mark.django_db
def test_seed_roles_adds_quality_permissions_without_duplicates():
    call_command("seed_roles", verbosity=0)
    first = PermissionCode.objects.filter(code__startswith="quality.").count()
    call_command("seed_roles", verbosity=0)
    second = PermissionCode.objects.filter(code__startswith="quality.").count()
    assert first == second == 2
    auditor = Role.objects.get(code="auditor")
    assert auditor.permissions.filter(code="quality.view").exists()
    assert not auditor.permissions.filter(code="quality.run").exists()


def test_profiles_are_allowlisted_and_release_is_superset():
    root = Path(settings.BASE_DIR)
    quick = {step.code for step in _selected_steps(root, "quick")}
    full = {step.code for step in _selected_steps(root, "full")}
    release = {step.code for step in _selected_steps(root, "release")}
    assert quick < full < release
    assert "tests.smoke" in quick
    assert "tests.full" in full
    assert {"database.migrate", "seeds.idempotency", "nginx.syntax", "package.clean"} <= release
    with pytest.raises(ValueError):
        _selected_steps(root, "rm-rf")


def test_qa_output_redacts_secret_values():
    env = {"SECRET_KEY": "very-secret-value", "VINOVA_API_TOKEN_PEPPER": "another-secret-value"}
    sanitized = redact(
        "SECRET_KEY=very-secret-value token: another-secret-value authorization=Bearer-123",
        env=env,
    )
    assert "very-secret-value" not in sanitized
    assert "another-secret-value" not in sanitized
    assert "Bearer-123" not in sanitized
    assert sanitized.count("[REDACTADO]") >= 3


def test_quality_routes_and_qa_compose_are_connected():
    assert resolve("/dashboard/quality/").view_name == "quality:run_list"
    assert resolve("/api/v1/quality/runs/").view_name == "api_v1:quality-api:run_list"
    compose = yaml.safe_load((Path(settings.BASE_DIR) / "docker-compose.qa.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    assert {"qa_db", "qa_redis", "qa_runner", "qa_worker"} <= set(services)
    assert "qa" in services["qa_worker"]["profiles"]
    assert "qa" in services["qa_runner"]["profiles"]
    assert services["qa_worker"]["command"].endswith("--concurrency=1")
    for service_name in ("qa_runner", "qa_worker"):
        service = services[service_name]
        assert all("docker.sock" not in str(volume) for volume in service["volumes"])
        assert "no-new-privileges:true" in service["security_opt"]
        assert "ALL" in service["cap_drop"]
        assert "qa_internal" in service["networks"]
        assert "db" not in service["depends_on"]
        assert {"qa_db", "qa_redis"} <= set(service["depends_on"])
    assert "/var/lib/postgresql/data" in services["qa_db"]["tmpfs"]
    assert "/data" in services["qa_redis"]["tmpfs"]
    assert "qa_internal" in services["qa_db"]["networks"]
    assert "qa_internal" in services["qa_redis"]["networks"]
    assert not services["qa_db"].get("ports")
    assert not services["qa_redis"].get("ports")
    assert compose["networks"]["qa_internal"]["internal"] is True


def test_quality_task_has_dedicated_queue(settings):
    assert settings.CELERY_TASK_ROUTES["apps.quality.tasks.run_quality_profile_task"]["queue"] == "qa"
    assert settings.CELERY_QA_QUEUE == "qa"


def test_release_ready_requires_release_profile_and_isolated_postgres():
    quick = QualityRun(profile="quick", status=QualityRun.Status.PASSED, failed_count=0, summary={"release_ready": True})
    release_sqlite = QualityRun(
        profile="release",
        status=QualityRun.Status.PASSED,
        failed_count=0,
        summary={"release_ready": False, "database": {"engine": "sqlite", "isolated": False}},
    )
    release_postgres = QualityRun(
        profile="release",
        status=QualityRun.Status.PASSED,
        failed_count=0,
        summary={"release_ready": True, "database": {"engine": "postgresql", "isolated": True}},
    )
    assert not quick.release_ready
    assert not release_sqlite.release_ready
    assert release_postgres.release_ready


def test_seed_idempotency_command_refuses_non_qa_environment(monkeypatch):
    monkeypatch.delenv("VINOVA_QA_ACTIVE", raising=False)
    with pytest.raises(CommandError, match="runner QA aislado"):
        call_command("check_seed_idempotency")


@pytest.mark.django_db
def test_disabled_api_reports_persisted_error_status(client, django_user_model, settings):
    settings.VINOVA_QA_EXECUTION_ENABLED = False
    user = django_user_model.objects.create_superuser(
        username="qa-disabled-superadmin",
        email="qa-disabled@example.com",
        password="safe-test-password",
    )
    client.force_login(user)
    response = client.post(
        reverse("api_v1:quality-api:run_create"),
        {"profile": "quick"},
        content_type="application/json",
    )
    assert response.status_code == 503
    assert response.json()["status"] == QualityRun.Status.ERROR
    assert QualityRun.objects.get().status == QualityRun.Status.ERROR


def test_runner_environment_does_not_inherit_company_secrets(monkeypatch):
    monkeypatch.setenv("SMTP_PASSWORD", "company-mail-secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://company:secret@production/db")
    env = _safe_environment(Path(settings.BASE_DIR), profile="quick")
    assert "SMTP_PASSWORD" not in env
    assert "company-mail-secret" not in env.values()
    assert "postgresql://company:secret@production/db" not in env.values()
    assert env["DJANGO_SETTINGS_MODULE"] == "config.settings.test"


def test_report_paths_are_stored_relative_to_private_root(tmp_path, settings):
    settings.VINOVA_QA_REPORT_ROOT = tmp_path
    report = tmp_path / "qa-example.json"
    report.write_text("{}", encoding="utf-8")
    assert _safe_report_relative_path(report.name) == report.name
    assert _safe_report_relative_path(str(report)) == report.name
    with pytest.raises(ValueError, match="fuera del almacenamiento privado"):
        _safe_report_relative_path(str(tmp_path.parent / "outside.json"))


def test_redaction_covers_database_urls_and_access_keys():
    env = {
        "TEST_DATABASE_URL": "postgresql://qa:qa-password@qa_db/postgres",
        "AWS_ACCESS_KEY_ID": "AKIA-TEST-ACCESS-KEY",
    }
    sanitized = redact("DB=postgresql://qa:qa-password@qa_db/postgres key=AKIA-TEST-ACCESS-KEY", env=env)
    assert "qa-password" not in sanitized
    assert "AKIA-TEST-ACCESS-KEY" not in sanitized


@pytest.mark.django_db
def test_stale_run_is_closed_and_no_longer_blocks(settings):
    settings.VINOVA_QA_STALE_AFTER_MINUTES = 30
    stale = QualityRun.objects.create(profile="quick", status=QualityRun.Status.RUNNING)
    old = timezone.now() - timezone.timedelta(hours=2)
    QualityRun.objects.filter(pk=stale.pk).update(started_at=old, created_at=old)
    assert expire_stale_quality_runs() == 1
    stale.refresh_from_db()
    assert stale.status == QualityRun.Status.ERROR
    replacement = create_quality_run(profile="quick", trigger=QualityRun.Trigger.CLI)
    assert replacement.status == QualityRun.Status.QUEUED


@pytest.mark.django_db
def test_expired_evidence_is_removed_but_summary_is_retained(tmp_path, settings):
    settings.VINOVA_QA_REPORT_ROOT = tmp_path
    settings.VINOVA_QA_RETENTION_DAYS = 30
    run = QualityRun.objects.create(
        profile="release",
        status=QualityRun.Status.PASSED,
        report_json_path="old.json",
        report_html_path="old.html",
        summary={"release_ready": True},
    )
    old = timezone.now() - timezone.timedelta(days=45)
    QualityRun.objects.filter(pk=run.pk).update(completed_at=old)
    (tmp_path / "old.json").write_text("{}", encoding="utf-8")
    (tmp_path / "old.html").write_text("<html></html>", encoding="utf-8")
    QualityCheckResult.objects.create(
        run=run,
        code="test",
        category="QA",
        title="Prueba",
        status=QualityCheckResult.Status.PASSED,
        output_excerpt="evidencia detallada",
    )
    assert cleanup_expired_quality_evidence() == 1
    run.refresh_from_db()
    assert run.report_json_path == run.report_html_path == ""
    assert run.summary["release_ready"] is True
    assert "evidence_purged_at" in run.summary
    assert run.checks.get().output_excerpt == ""
    assert not (tmp_path / "old.json").exists()


@pytest.mark.django_db
def test_quality_run_creation_uses_a_cross_process_lock():
    cache.set(QUALITY_RUN_CREATE_LOCK_KEY, "busy", timeout=30)
    try:
        with pytest.raises(ValueError, match="Otra solicitud QA"):
            create_quality_run(profile="quick", trigger=QualityRun.Trigger.CLI)
    finally:
        cache.delete(QUALITY_RUN_CREATE_LOCK_KEY)
