"""ES: Este módulo especifica regresiones ejecutables para el dominio de auditoría.

EN: This module specifies executable regressions for the audit domain.

Contexto existente / Existing context:
Regression coverage for audit action scope v170 in the audit domain.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.audit.models import SecurityAlert
from apps.audit.selectors import scoped_audit_queryset
from apps.audit.services import audit_log
from apps.branches.models import Branch
from apps.companies.models import Company


@pytest.fixture
def scoped_auditor(django_user_model):
    company = Company.objects.create(legal_name="Audit Scope SA", commercial_name="Audit Scope", ruc="1799999999003")
    branch_a = Branch.objects.create(company=company, name="Norte", code="AUD-A", branch_type=Branch.BranchType.DEALERSHIP, city="Quito")
    branch_b = Branch.objects.create(company=company, name="Sur", code="AUD-B", branch_type=Branch.BranchType.DEALERSHIP, city="Quito")
    user = django_user_model.objects.create_user(username="auditor-scope", email="auditor-scope@example.com", password="x")
    view_permission = PermissionCode.objects.create(module="audit", code="audit.view", name="View")
    export_permission = PermissionCode.objects.create(module="audit", code="audit.export", name="Export")
    manage_permission = PermissionCode.objects.create(module="audit", code="audit.manage_alerts", name="Manage")
    view_role = Role.objects.create(code="audit_view_global", name="Global audit view")
    view_role.permissions.add(view_permission)
    action_role = Role.objects.create(code="audit_actions_branch", name="Branch audit actions")
    action_role.permissions.add(export_permission, manage_permission)
    UserRole.objects.create(user=user, role=view_role)
    UserRole.objects.create(user=user, role=action_role, branch=branch_a)
    return user, branch_a, branch_b


@pytest.mark.django_db
def test_export_uses_export_scope_not_broader_view_scope(client, scoped_auditor):
    user, branch_a, branch_b = scoped_auditor
    allowed = audit_log(user=None, action="scope.allowed", branch=branch_a)
    denied = audit_log(user=None, action="scope.denied", branch=branch_b)
    assert scoped_audit_queryset(user).filter(pk__in=[allowed.pk, denied.pk]).count() == 2
    assert list(
        scoped_audit_queryset(user, permission_code="audit.export")
        .filter(pk__in=[allowed.pk, denied.pk])
        .values_list("pk", flat=True)
    ) == [allowed.pk]

    client.force_login(user)
    response = client.get(reverse("audit_internal:export") + "?format=csv")
    assert response.status_code == 200
    content = response.content.decode("utf-8-sig")
    assert "scope.allowed" in content
    assert "scope.denied" not in content


@pytest.mark.django_db
def test_alert_mutation_uses_manage_scope(client, scoped_auditor):
    user, branch_a, branch_b = scoped_auditor
    log = audit_log(user=None, action="security.permission_denied", branch=branch_b, after={"status_code": 403})
    alert = SecurityAlert.objects.get(audit_log=log)
    client.force_login(user)
    response = client.post(
        reverse("audit_internal:alert_update", kwargs={"alert_id": alert.alert_id}),
        {"status": SecurityAlert.Status.RESOLVED, "resolution_notes": "No autorizado"},
    )
    assert response.status_code == 404
    alert.refresh_from_db()
    assert alert.status == SecurityAlert.Status.OPEN
