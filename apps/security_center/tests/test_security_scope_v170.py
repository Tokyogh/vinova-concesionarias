"""ES: Este módulo especifica regresiones ejecutables para el dominio de seguridad.

EN: This module specifies executable regressions for the security center domain.

Contexto existente / Existing context:
Regression coverage for security scope v170 in the security_center domain.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.security_center.models import ActiveSession


@pytest.fixture
def scoped_security_users(django_user_model):
    company = Company.objects.create(legal_name="Security Scope SA", commercial_name="Security Scope", ruc="1799999999004")
    branch_a = Branch.objects.create(company=company, name="Norte", code="SEC-A", branch_type=Branch.BranchType.DEALERSHIP, city="Quito")
    branch_b = Branch.objects.create(company=company, name="Sur", code="SEC-B", branch_type=Branch.BranchType.DEALERSHIP, city="Quito")
    view_permission = PermissionCode.objects.create(module="security", code="security.view", name="View security")
    manage_permission = PermissionCode.objects.create(module="security", code="security.manage", name="Manage security")
    security_role = Role.objects.create(code="branch_security", name="Branch security")
    security_role.permissions.add(view_permission, manage_permission)
    employee_role = Role.objects.create(code="security_employee", name="Employee")
    manager = django_user_model.objects.create_user(username="security-manager", email="security-manager@example.com", password="x")
    employee_a = django_user_model.objects.create_user(username="employee-a", email="employee-a@example.com", password="x")
    employee_b = django_user_model.objects.create_user(username="employee-b", email="employee-b@example.com", password="x")
    UserRole.objects.create(user=manager, role=security_role, branch=branch_a)
    UserRole.objects.create(user=employee_a, role=employee_role, branch=branch_a)
    UserRole.objects.create(user=employee_b, role=employee_role, branch=branch_b)
    ActiveSession.objects.create(user=employee_a, session_key="session-a")
    ActiveSession.objects.create(user=employee_b, session_key="session-b")
    return manager, employee_a, employee_b


@pytest.mark.django_db
def test_security_sessions_api_and_dashboard_are_branch_scoped(client, scoped_security_users):
    manager, employee_a, employee_b = scoped_security_users
    client.force_login(manager)
    response = client.get("/api/security-sessions/")
    assert response.status_code == 200
    user_ids = {item["user"] for item in response.json()["results"]}
    assert employee_a.pk in user_ids
    assert employee_b.pk not in user_ids

    response = client.get(reverse("security_center:dashboard"))
    assert response.status_code == 200
    recent_user_ids = {session.user_id for session in response.context["recent_sessions"]}
    assert employee_a.pk in recent_user_ids
    assert employee_b.pk not in recent_user_ids


@pytest.mark.django_db
def test_branch_security_manager_cannot_reset_other_branch_or_global_policy(client, scoped_security_users):
    manager, employee_a, employee_b = scoped_security_users
    client.force_login(manager)
    response = client.post(reverse("security_center:admin_reset_2fa", kwargs={"pk": employee_b.pk}))
    assert response.status_code == 404
    response = client.post(reverse("security_center:policy"), {})
    assert response.status_code == 403
