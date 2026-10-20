"""ES: Este módulo especifica regresiones ejecutables para el dominio de cuentas.

EN: This module specifies executable regressions for the accounts domain.

Contexto existente / Existing context:
Regression coverage for html management scope v200 in the accounts domain.
"""

from __future__ import annotations

import pytest

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company

pytestmark = pytest.mark.django_db


@pytest.fixture
def manage_permissions():
    manage = PermissionCode.objects.create(module="accounts", code="accounts.manage_users", name="Manage users")
    assign = PermissionCode.objects.create(module="accounts", code="accounts.assign_roles", name="Assign roles")
    roles = PermissionCode.objects.create(module="accounts", code="accounts.roles.view", name="View roles")
    return manage, assign, roles


@pytest.fixture
def management_scope(django_user_model, manage_permissions):
    manage, assign, roles = manage_permissions
    company = Company.objects.create(
        legal_name="Gestión HTML Scope S.A.", commercial_name="Ghs", ruc="1799999999002"
    )
    branch_a = Branch.objects.create(
        company=company, name="Norte Gestión", code="ACC-A", branch_type=Branch.BranchType.DEALERSHIP, city="Quito"
    )
    branch_b = Branch.objects.create(
        company=company, name="Sur Gestión", code="ACC-B", branch_type=Branch.BranchType.DEALERSHIP, city="Quito"
    )
    manager_a_role = Role.objects.create(code="admin-sucursal-a", name="Admin sucursal A")
    manager_a_role.permissions.add(manage, assign)
    manager_b_role = Role.objects.create(code="admin-sucursal-b", name="Admin sucursal B")
    manager_b_role.permissions.add(manage, assign)

    manager_a = django_user_model.objects.create_user(
        username="manager-a", email="manager-a@example.com", password="x"
    )
    manager_b = django_user_model.objects.create_user(
        username="manager-b", email="manager-b@example.com", password="x"
    )
    employee_a = django_user_model.objects.create_user(
        username="employee-a", email="employee-a@example.com", password="x", branch=branch_a
    )
    employee_b = django_user_model.objects.create_user(
        username="employee-b", email="employee-b@example.com", password="x", branch=branch_b
    )
    UserRole.objects.create(user=manager_a, role=manager_a_role, branch=branch_a)
    UserRole.objects.create(user=manager_b, role=manager_b_role, branch=branch_b)
    emp_role = Role.objects.create(code="vendedor", name="Vendedor")
    emp_role.permissions.add(roles)
    UserRole.objects.create(user=employee_a, role=emp_role, branch=branch_a)
    UserRole.objects.create(user=employee_b, role=emp_role, branch=branch_b)
    return branch_a, branch_b, manager_a, manager_b, employee_a, employee_b


def test_user_list_is_branch_scoped(client, management_scope):
    branch_a, branch_b, manager_a, manager_b, employee_a, employee_b = management_scope
    client.force_login(manager_a)

    response = client.get("/accounts/users/")
    assert response.status_code == 200
    content = response.content.decode()
    assert f"/accounts/users/{employee_a.pk}/" in content
    assert f"/accounts/users/{employee_b.pk}/" not in content
    assert f"/accounts/users/{manager_b.pk}/" not in content


def test_user_detail_direct_other_branch_returns_404(client, management_scope):
    branch_a, branch_b, manager_a, manager_b, employee_a, employee_b = management_scope
    client.force_login(manager_a)

    assert client.get(f"/accounts/users/{employee_b.pk}/").status_code == 404
    assert client.get(f"/accounts/users/{manager_b.pk}/").status_code == 404
    assert client.get(f"/accounts/users/{employee_a.pk}/").status_code == 200


def test_user_detail_has_plain_title_and_unique_security_section(client, management_scope):
    branch_a, branch_b, manager_a, manager_b, employee_a, employee_b = management_scope
    client.force_login(manager_a)

    response = client.get(f"/accounts/users/{employee_a.pk}/")
    content = response.content.decode()

    assert response.status_code == 200
    assert f"<title>{employee_a.username} | Vinova Pro</title>" in content
    assert "<section" not in content.split("</title>", 1)[0]
    assert content.count("<h2>Seguridad avanzada</h2>") == 1


def test_user_actions_direct_other_branch_returns_404(client, management_scope):
    branch_a, branch_b, manager_a, manager_b, employee_a, employee_b = management_scope
    client.force_login(manager_a)

    assert client.post(f"/accounts/users/{employee_b.pk}/toggle-active/").status_code == 404
    assert client.post(f"/accounts/users/{employee_b.pk}/password/", {"password1": "x", "password2": "x"}).status_code == 404


def test_role_assignment_limited_to_own_branch_users(client, management_scope, manage_permissions):
    branch_a, branch_b, manager_a, manager_b, employee_a, employee_b = management_scope
    manage, assign, roles = manage_permissions
    role_to_assign = Role.objects.create(code="facturacion", name="Facturación")
    role_to_assign.permissions.add(manage, assign)
    client.force_login(manager_a)

    response = client.post(
        f"/accounts/users/{employee_b.pk}/roles/add/",
        {"role": role_to_assign.pk, "branch": branch_b.pk},
    )
    assert response.status_code == 404

    ok = client.post(
        f"/accounts/users/{employee_a.pk}/roles/add/",
        {"role": role_to_assign.pk, "branch": branch_a.pk},
    )
    assert ok.status_code == 302
    assert UserRole.objects.filter(user=employee_a, role=role_to_assign, branch=branch_a, is_active=True).exists()


def test_role_remove_limited_to_own_branch(client, management_scope):
    branch_a, branch_b, manager_a, manager_b, employee_a, employee_b = management_scope
    role_b = Role.objects.create(code="auditor-b", name="Auditor B")
    user_role_b = UserRole.objects.create(user=employee_b, role=role_b, branch=branch_b)
    client.force_login(manager_a)

    response = client.post(f"/accounts/users/{employee_b.pk}/roles/{user_role_b.pk}/remove/")
    assert response.status_code == 404
    user_role_b.refresh_from_db()
    assert user_role_b.is_active


def test_global_manager_sees_all_users(client, management_scope, django_user_model, manage_permissions):
    branch_a, branch_b, manager_a, manager_b, employee_a, employee_b = management_scope
    manage, assign, roles = manage_permissions
    global_role = Role.objects.create(code="admin-global", name="Admin global")
    global_role.permissions.add(manage, assign)
    global_manager = django_user_model.objects.create_user(
        username="manager-global", email="manager-global@example.com", password="x"
    )
    UserRole.objects.create(user=global_manager, role=global_role)
    client.force_login(global_manager)

    response = client.get("/accounts/users/")
    assert response.status_code == 200
    content = response.content.decode()
    assert f"/accounts/users/{employee_a.pk}/" in content
    assert f"/accounts/users/{employee_b.pk}/" in content
    assert client.get(f"/accounts/users/{employee_b.pk}/").status_code == 200
