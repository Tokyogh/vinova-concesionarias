"""ES: Este módulo especifica regresiones ejecutables para el dominio de cuentas.

EN: This module specifies executable regressions for the accounts domain.

Contexto existente / Existing context:
Regression coverage for api scope v170 in the accounts domain.
"""

from __future__ import annotations

import pytest

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.api.models import APIClient, APIScope
from apps.api.services import issue_api_client_token
from apps.branches.models import Branch
from apps.companies.models import Company


pytestmark = pytest.mark.django_db


def build_scope(django_user_model):
    company = Company.objects.create(
        legal_name="Account API Scope SA",
        commercial_name="Account API Scope",
        ruc="1799999999006",
    )
    branch_a = Branch.objects.create(
        company=company,
        name="Norte",
        code="ACC-A",
        branch_type=Branch.BranchType.DEALERSHIP,
        city="Quito",
    )
    branch_b = Branch.objects.create(
        company=company,
        name="Sur",
        code="ACC-B",
        branch_type=Branch.BranchType.DEALERSHIP,
        city="Quito",
    )
    manage = PermissionCode.objects.create(module="accounts", code="accounts.manage_users", name="Manage users")
    assign = PermissionCode.objects.create(module="accounts", code="accounts.assign_roles", name="Assign roles")
    manager_role = Role.objects.create(code="account-api-manager", name="Account API manager")
    manager_role.permissions.add(manage, assign)
    employee_role = Role.objects.create(code="account-api-employee", name="Account API employee")
    manager = django_user_model.objects.create_user(
        username="account-api-manager",
        email="account-api-manager@example.com",
        password="test12345",
    )
    employee_a = django_user_model.objects.create_user(
        username="account-api-a",
        email="account-api-a@example.com",
        password="test12345",
    )
    employee_b = django_user_model.objects.create_user(
        username="account-api-b",
        email="account-api-b@example.com",
        password="test12345",
    )
    UserRole.objects.create(user=manager, role=manager_role, branch=branch_a)
    UserRole.objects.create(user=employee_a, role=employee_role, branch=branch_a)
    UserRole.objects.create(user=employee_b, role=employee_role, branch=branch_b)
    return manager, employee_a, employee_b, manager_role


def test_users_api_is_read_only_and_branch_scoped(client, django_user_model):
    manager, employee_a, employee_b, _ = build_scope(django_user_model)
    client.force_login(manager)

    response = client.get("/api/users/")

    assert response.status_code == 200
    user_ids = {item["id"] for item in response.json()["results"]}
    assert employee_a.pk in user_ids
    assert employee_b.pk not in user_ids
    assert client.post("/api/users/", {"username": "bypass"}).status_code == 405


def test_roles_api_requires_global_assignment_permission(client, django_user_model):
    manager, _, _, _ = build_scope(django_user_model)
    client.force_login(manager)

    assert client.get("/api/roles/").status_code == 403


def test_staff_flag_does_not_replace_business_permission(client, django_user_model):
    staff = django_user_model.objects.create_user(
        username="account-api-staff",
        email="account-api-staff@example.com",
        password="test12345",
        is_staff=True,
    )
    client.force_login(staff)

    assert client.get("/api/users/").status_code == 403


def test_global_role_manager_can_read_but_not_mutate_roles(client, django_user_model):
    manager, _, _, manager_role = build_scope(django_user_model)
    UserRole.objects.filter(user=manager).update(branch=None)
    client.force_login(manager)

    response = client.get("/api/roles/")

    assert response.status_code == 200
    assert manager_role.pk in {item["id"] for item in response.json()["results"]}
    assert client.post("/api/roles/", {"code": "bypass", "name": "Bypass"}).status_code == 405


def test_branch_bound_api_client_uses_role_branch_not_legacy_user_branch(client, django_user_model):
    manager, employee_a, employee_b, _ = build_scope(django_user_model)
    UserRole.objects.filter(user=manager).update(branch=None)
    scope = APIScope.objects.create(code="users:read", name="Users read")
    credential = APIClient.objects.create(
        name="Branch user directory",
        service_user=manager,
        branch=UserRole.objects.get(user=employee_a).branch,
        allowed_ip_networks="127.0.0.1/32",
    )
    credential.scopes.add(scope)
    token = issue_api_client_token(credential, actor=manager)

    response = client.get("/api/users/", HTTP_AUTHORIZATION=f"Bearer {token}")

    assert response.status_code == 200
    user_ids = {item["id"] for item in response.json()["results"]}
    assert employee_a.pk in user_ids
    assert employee_b.pk not in user_ids
