"""ES: Este módulo especifica regresiones ejecutables para el dominio de continuidad.

EN: This module specifies executable regressions for the continuity domain.

Contexto existente / Existing context:
Regression coverage for continuity scope v170 in the continuity domain.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.audit.models import AuditLog
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.continuity.models import BackupPolicy


pytestmark = pytest.mark.django_db


def make_continuity_user(django_user_model, *, branch=None):
    user = django_user_model.objects.create_user(
        username="continuity-scope",
        email="continuity-scope@example.com",
        password="test12345",
    )
    role = Role.objects.create(code="continuity-scope", name="Continuity scope")
    permissions = [
        PermissionCode.objects.create(module="continuity", code=code, name=code)
        for code in ("continuity.view", "continuity.manage", "continuity.restore")
    ]
    role.permissions.set(permissions)
    UserRole.objects.create(user=user, role=role, branch=branch)
    return user


def test_branch_scoped_continuity_role_cannot_access_system_backups(client, django_user_model):
    company = Company.objects.create(
        legal_name="Continuity Scope SA",
        commercial_name="Continuity Scope",
        ruc="1799999999005",
    )
    branch = Branch.objects.create(
        company=company,
        name="Principal",
        code="CONT-A",
        branch_type=Branch.BranchType.DEALERSHIP,
        city="Quito",
    )
    user = make_continuity_user(django_user_model, branch=branch)
    client.force_login(user)

    assert client.get(reverse("continuity:dashboard")).status_code == 403
    assert client.get("/api/backups/").status_code == 403
    assert client.post(reverse("continuity:backup_create"), {"backup_type": "files"}).status_code == 403
    assert client.post(reverse("continuity:policy"), {}).status_code == 403


def test_global_continuity_manager_updates_policy_with_audit(client, django_user_model):
    user = make_continuity_user(django_user_model)
    policy = BackupPolicy.objects.filter(is_active=True).first()
    client.force_login(user)

    response = client.post(
        reverse("continuity:policy"),
        {
            "name": policy.name,
            "is_active": "on",
            "frequency": BackupPolicy.Frequency.WEEKLY,
            "retention_days": 45,
            "include_database": "on",
            "include_media": "on",
            "include_private": "on",
            "external_copy_required": "on",
            "destination_hint": "Almacenamiento externo administrado",
            "notes": "Revisión v1.7",
        },
    )

    assert response.status_code == 302
    policy.refresh_from_db()
    assert policy.retention_days == 45
    event = AuditLog.objects.get(action="continuity.policy.updated", object_id=str(policy.pk))
    assert event.user == user
    assert event.before["retention_days"] != event.after["retention_days"]
    assert event.is_sensitive is True
