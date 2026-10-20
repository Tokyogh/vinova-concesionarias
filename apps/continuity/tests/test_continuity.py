"""ES: Este módulo especifica regresiones ejecutables para el dominio de continuidad.

EN: This module specifies executable regressions for the continuity domain.

Contexto existente / Existing context:
Regression coverage for continuity in the continuity domain.
"""

import json
from collections import namedtuple

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.continuity.models import BackupRecord
from apps.continuity.services import (
    backup_restore_compatibility,
    create_backup_record,
    execute_backup,
    verify_backup,
)
from apps.continuity.update_center import update_agent_status


pytestmark = pytest.mark.django_db


def make_user(django_user_model, *permissions):
    user = django_user_model.objects.create_user(
        username="continuity-admin", email="continuity@example.com", password="test12345"
    )
    role = Role.objects.create(code="continuity-test", name="Continuity test", level=2)
    perms = [PermissionCode.objects.create(module=code.split(".")[0], code=code, name=code) for code in permissions]
    role.permissions.set(perms)
    UserRole.objects.create(user=user, role=role)
    return user


def test_create_and_verify_files_backup(tmp_path, django_user_model):
    user = make_user(django_user_model, "continuity.view", "continuity.manage")
    media = tmp_path / "media"
    private = tmp_path / "private"
    media.mkdir()
    private.mkdir()
    (media / "vehicle.jpg").write_bytes(b"image")
    (private / "contract.pdf").write_bytes(b"private")

    with override_settings(MEDIA_ROOT=media, PRIVATE_STORAGE_ROOT=private):
        record = create_backup_record(actor=user, backup_type=BackupRecord.BackupType.FILES, notes="test")
        execute_backup(record)
        record.refresh_from_db()
        assert record.status == BackupRecord.Status.COMPLETED
        assert record.manifest["backup_format_version"] == 3
        assert record.manifest["inventory"]
        assert record.manifest["database_migration_state"]["kind"] == "django-migration-ledger"
        assert record.sha256
        assert (private / record.archive_path).exists()
        result = verify_backup(record, actor=user)
        assert result["valid"] is True
        assert result["compatible"] is True
        record.refresh_from_db()
        assert record.status == BackupRecord.Status.VERIFIED


def test_restore_preparation_rejects_insufficient_disk_space(tmp_path, django_user_model, monkeypatch):
    user = make_user(django_user_model, "continuity.view", "continuity.manage", "continuity.restore")
    media = tmp_path / "media"
    private = tmp_path / "private"
    destination = tmp_path / "restore"
    media.mkdir()
    private.mkdir()
    (private / "contract.pdf").write_bytes(b"private")
    usage = namedtuple("usage", "total used free")

    with override_settings(MEDIA_ROOT=media, PRIVATE_STORAGE_ROOT=private):
        record = create_backup_record(actor=user, backup_type=BackupRecord.BackupType.FILES)
        execute_backup(record)
        monkeypatch.setattr(
            "apps.continuity.management.commands.prepare_vinova_restore.shutil.disk_usage",
            lambda _path: usage(100, 100, 0),
        )
        with pytest.raises(CommandError, match="Espacio libre insuficiente"):
            call_command(
                "prepare_vinova_restore",
                str(record.public_id),
                destination=str(destination),
                confirm="PREPARE_RESTORE",
            )

    assert destination.exists()
    assert not any(destination.iterdir())


def test_continuity_dashboard_requires_permission(client, django_user_model):
    user = django_user_model.objects.create_user(username="plain", email="plain@example.com", password="test12345")
    client.force_login(user)
    response = client.get("/dashboard/continuity/")
    assert response.status_code == 403


def test_continuity_dashboard_visible_with_permission(client, django_user_model):
    user = make_user(django_user_model, "continuity.view")
    client.force_login(user)
    response = client.get("/dashboard/continuity/")
    assert response.status_code == 200
    assert "Continuidad y recuperación" in response.content.decode()


def test_backup_is_queued_with_celery_task_id(monkeypatch, django_user_model):
    from apps.continuity.dispatch import enqueue_backup

    user = make_user(django_user_model, "continuity.view", "continuity.manage")
    record = create_backup_record(actor=user, backup_type=BackupRecord.BackupType.FILES)

    class Result:
        id = "task-123"

    monkeypatch.setattr("apps.continuity.dispatch.run_backup_task.apply_async", lambda *args, **kwargs: Result())
    result = enqueue_backup(record, allow_sync_fallback=False)

    record.refresh_from_db()
    assert result.queued is True
    assert result.used_sync_fallback is False
    assert record.status == BackupRecord.Status.PENDING
    assert record.execution_mode == BackupRecord.ExecutionMode.ASYNC
    assert record.celery_task_id == "task-123"
    assert record.queued_at is not None


def test_backup_queue_failure_fails_closed_without_fallback(monkeypatch, django_user_model):
    from apps.continuity.dispatch import enqueue_backup

    user = make_user(django_user_model, "continuity.view", "continuity.manage")
    record = create_backup_record(actor=user, backup_type=BackupRecord.BackupType.FILES)

    def unavailable(*args, **kwargs):
        raise ConnectionError("redis://user:secret@redis:6379/0")

    monkeypatch.setattr("apps.continuity.dispatch.run_backup_task.apply_async", unavailable)
    result = enqueue_backup(record, allow_sync_fallback=False)

    record.refresh_from_db()
    assert result.queued is False
    assert result.used_sync_fallback is False
    assert record.status == BackupRecord.Status.FAILED
    assert "secret" not in record.queue_error
    assert "Redis" in record.error_message


def test_backup_queue_failure_can_use_explicit_local_fallback(monkeypatch, django_user_model):
    from apps.continuity.dispatch import enqueue_backup

    user = make_user(django_user_model, "continuity.view", "continuity.manage")
    record = create_backup_record(actor=user, backup_type=BackupRecord.BackupType.FILES)

    def unavailable(*args, **kwargs):
        raise ConnectionError("broker unavailable")

    def fake_execute(current):
        current.status = BackupRecord.Status.COMPLETED
        current.save(update_fields=["status", "updated_at"])
        return current

    monkeypatch.setattr("apps.continuity.dispatch.run_backup_task.apply_async", unavailable)
    monkeypatch.setattr("apps.continuity.dispatch.execute_backup", fake_execute)
    result = enqueue_backup(record, allow_sync_fallback=True)

    record.refresh_from_db()
    assert result.used_sync_fallback is True
    assert record.status == BackupRecord.Status.COMPLETED
    assert record.execution_mode == BackupRecord.ExecutionMode.SYNC_FALLBACK


def test_policy_scheduler_is_disabled_by_default(settings):
    from apps.continuity.tasks import schedule_policy_backups

    settings.VINOVA_AUTOMATED_BACKUPS_ENABLED = False
    assert schedule_policy_backups() == {"enabled": False, "scheduled": False}


def test_backup_restore_compatibility_fails_closed_for_version_mismatch():
    newer = backup_restore_compatibility({"product": "Vinova Pro", "product_version": "99.0.0"})
    older = backup_restore_compatibility({"product": "Vinova Pro", "product_version": "1.9.0"})
    authorized = backup_restore_compatibility(
        {"product": "Vinova Pro", "product_version": "1.9.0"},
        allow_forward_migration=True,
    )

    assert not newer["compatible"]
    assert not older["compatible"]
    assert authorized["compatible"]


def test_update_center_shows_real_state_without_fake_action(client, django_user_model, settings):
    settings.VINOVA_RELEASE_MANIFEST_PATH = ""
    settings.VINOVA_RELEASE_ARTIFACT_PATH = ""
    settings.VINOVA_RELEASE_PUBLIC_KEY_PATH = ""
    settings.VINOVA_RELEASE_TRUSTED_KEY_ID = ""
    settings.VINOVA_UPDATE_AGENT_STATUS_FILE = ""
    user = make_user(django_user_model, "continuity.view")
    client.force_login(user)

    response = client.get("/dashboard/continuity/updates/")
    content = response.content.decode()

    assert response.status_code == 200
    assert settings.VINOVA_PRODUCT_VERSION in content
    assert "No hay un release real configurado" in content
    assert "Update Agent no configurado" in content
    assert "Actualizar ahora" not in content


def test_update_agent_status_reads_only_allowlisted_fields(tmp_path, settings):
    status_file = tmp_path / "agent-status.json"
    status_file.write_text(
        json.dumps(
            {
                "state": "failed",
                "message": "Health check bloqueado",
                "target_version": "2.1.0",
                "updated_at": "2026-10-07T12:00:00Z",
                "secret": "must-not-render",
            }
        ),
        encoding="utf-8",
    )
    settings.VINOVA_UPDATE_AGENT_STATUS_FILE = str(status_file)

    status = update_agent_status()

    assert status["connected"]
    assert status["state"] == "failed"
    assert status["state_label"] == "Fallido"
    assert "secret" not in status


def test_update_center_sanitizes_invalid_external_paths(client, django_user_model, settings, tmp_path):
    hidden_path = tmp_path / "internal-release-location" / "missing.json"
    settings.VINOVA_RELEASE_MANIFEST_PATH = str(hidden_path)
    settings.VINOVA_RELEASE_ARTIFACT_PATH = str(tmp_path / "release.tar.gz")
    settings.VINOVA_RELEASE_PUBLIC_KEY_PATH = str(tmp_path / "release.pem")
    settings.VINOVA_RELEASE_TRUSTED_KEY_ID = "release-2026"
    user = make_user(django_user_model, "continuity.view")
    client.force_login(user)

    response = client.get("/dashboard/continuity/updates/")
    content = response.content.decode()

    assert response.status_code == 200
    assert "El release configurado no es válido o no puede verificarse" in content
    assert str(hidden_path) not in content
