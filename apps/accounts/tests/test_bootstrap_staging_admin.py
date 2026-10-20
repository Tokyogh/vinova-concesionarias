"""ES: Este módulo especifica regresiones ejecutables para el dominio de cuentas.

EN: This module specifies executable regressions for the accounts domain.

Contexto existente / Existing context:
Regression coverage for bootstrap staging admin in the accounts domain.
"""

from __future__ import annotations

import io

import pytest
from django.core.management import call_command

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def test_bootstrap_staging_admin_creates_and_repairs_account(monkeypatch):
    monkeypatch.setenv("VINOVA_ENVIRONMENT", "test")
    monkeypatch.setattr("sys.stdin", io.StringIO("VinovaAdmin2026*\n"))
    call_command(
        "bootstrap_staging_admin",
        username="elias-admin",
        email="elias@example.com",
        password_stdin=True,
        clear_login_cache=True,
        verbosity=0,
    )

    user = User.objects.get(username="elias-admin")
    assert user.check_password("VinovaAdmin2026*")
    assert user.is_active is True
    assert user.is_staff is True
    assert user.is_superuser is False
    assert user.has_role("admin_general")

    user.failed_login_count = 5
    user.save(update_fields=["failed_login_count"])
    monkeypatch.setattr("sys.stdin", io.StringIO("VinovaAdmin2027*\n"))
    call_command(
        "bootstrap_staging_admin",
        username="elias-admin",
        email="elias@example.com",
        password_stdin=True,
        clear_login_cache=True,
        verbosity=0,
    )
    user.refresh_from_db()
    assert user.check_password("VinovaAdmin2027*")
    assert user.failed_login_count == 0
