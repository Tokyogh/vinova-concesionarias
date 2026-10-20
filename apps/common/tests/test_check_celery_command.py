"""ES: Este módulo especifica regresiones ejecutables para el dominio de infraestructura compartida.

EN: This module specifies executable regressions for the common domain.

Contexto existente / Existing context:
Regression coverage for check celery command in the common domain.
"""

from __future__ import annotations

from contextlib import nullcontext
from io import StringIO
from unittest.mock import Mock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.common.management.commands.check_celery import normalize_registered_tasks


def test_normalize_registered_tasks_removes_celery_annotations():
    assert normalize_registered_tasks(
        [
            "apps.common.tasks.system_heartbeat",
            "apps.continuity.tasks.run_backup_task [rate_limit=2/h]",
        ]
    ) == {
        "apps.common.tasks.system_heartbeat",
        "apps.continuity.tasks.run_backup_task",
    }


def test_check_celery_accepts_registered_task_metadata():
    connection = Mock()
    inspector = Mock()
    inspector.ping.return_value = {"worker@test": {"ok": "pong"}}
    inspector.registered.return_value = {
        "worker@test": [
            "apps.common.tasks.system_heartbeat",
            "apps.continuity.tasks.run_backup_task [rate_limit=2/h]",
            "apps.continuity.tasks.schedule_policy_backups",
            "apps.api.tasks.deliver_webhook_task",
            "apps.quality.tasks.run_quality_profile_task",
            "apps.quality.tasks.schedule_automated_quality_run",
        ]
    }
    output = StringIO()

    with (
        patch("apps.common.management.commands.check_celery.celery_app.connection_for_read", return_value=nullcontext(connection)),
        patch("apps.common.management.commands.check_celery.celery_app.control.inspect", return_value=inspector),
    ):
        call_command("check_celery", stdout=output)

    connection.ensure_connection.assert_called_once_with(max_retries=1)
    assert "Tareas críticas verificadas: 6" in output.getvalue()


def test_check_celery_requires_each_critical_task_somewhere_in_cluster():
    connection = Mock()
    inspector = Mock()
    inspector.ping.return_value = {"worker@test": {"ok": "pong"}}
    inspector.registered.return_value = {
        "worker@test": [
            "apps.common.tasks.system_heartbeat",
            "apps.continuity.tasks.schedule_policy_backups",
            "apps.api.tasks.deliver_webhook_task",
        ]
    }

    with (
        patch("apps.common.management.commands.check_celery.celery_app.connection_for_read", return_value=nullcontext(connection)),
        patch("apps.common.management.commands.check_celery.celery_app.control.inspect", return_value=inspector),
        pytest.raises(CommandError, match="run_backup_task"),
    ):
        call_command("check_celery")
