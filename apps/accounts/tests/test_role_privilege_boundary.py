"""ES: Este módulo especifica regresiones ejecutables para el dominio de cuentas.

EN: This module specifies executable regressions for the accounts domain.

Contexto existente / Existing context:
Regression coverage for role privilege boundary in the accounts domain.
"""

from __future__ import annotations

import pytest
from django.core.exceptions import PermissionDenied

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.accounts.services import assign_role_to_user, remove_user_role
from apps.branches.models import Branch
from apps.companies.models import Company

pytestmark = pytest.mark.django_db


@pytest.fixture
def roles_setup(django_user_model):
    manage = PermissionCode.objects.create(module="accounts", code="accounts.manage_users", name="Gestionar usuarios")
    assign = PermissionCode.objects.create(module="accounts", code="accounts.assign_roles", name="Asignar roles")
    company = Company.objects.create(
        legal_name="Límite Roles S.A.", commercial_name="LimRol", ruc="1799999999003"
    )
    branch_a = Branch.objects.create(
        company=company, name="Norte Límite", code="RL-A", branch_type=Branch.BranchType.DEALERSHIP, city="Quito"
    )
    branch_b = Branch.objects.create(
        company=company, name="Sur Límite", code="RL-B", branch_type=Branch.BranchType.DEALERSHIP, city="Quito"
    )

    manager_role = Role.objects.create(code="admin_sucursal", level=10, name="Admin Sucursal")
    manager_role.permissions.add(manage, assign)
    manager_a = django_user_model.objects.create_user(username="manager-bound", email="manager-bound@example.com", password="x")
    UserRole.objects.create(user=manager_a, role=manager_role, branch=branch_a)

    admin_general = Role.objects.create(code="admin_general", level=5, name="Admin General")
    admin_general.permissions.add(manage, assign)
    global_manager = django_user_model.objects.create_user(username="manager-global", email="manager-global@example.com", password="x")
    UserRole.objects.create(user=global_manager, role=admin_general)

    auditor = Role.objects.create(code="auditor", level=80, name="Auditor solo lectura")
    vendedor = Role.objects.create(code="vendedor", level=30, name="Vendedor")
    employee = django_user_model.objects.create_user(username="employee-a", email="employee-a@example.com", password="x", branch=branch_a)

    return {
        "branch_a": branch_a,
        "branch_b": branch_b,
        "manager_a": manager_a,
        "global_manager": global_manager,
        "admin_general": admin_general,
        "auditor": auditor,
        "vendedor": vendedor,
        "employee": employee,
    }


def test_branch_manager_cannot_assign_global_role_via_post(client, roles_setup):
    employee = roles_setup["employee"]
    auditor = roles_setup["auditor"]
    client.force_login(roles_setup["manager_a"])

    response = client.post(f"/accounts/users/{employee.pk}/roles/add/", {"role": auditor.pk})

    assert response.status_code == 302
    assert not UserRole.objects.filter(user=employee, role=auditor).exists()


def test_branch_manager_cannot_assign_privileged_role(client, roles_setup):
    employee = roles_setup["employee"]
    admin_general = roles_setup["admin_general"]
    branch_a = roles_setup["branch_a"]
    client.force_login(roles_setup["manager_a"])

    response = client.post(
        f"/accounts/users/{employee.pk}/roles/add/", {"role": admin_general.pk, "branch": branch_a.pk}
    )
    assert response.status_code == 302
    assert not UserRole.objects.filter(user=employee, role=admin_general).exists()

    with pytest.raises(PermissionDenied):
        assign_role_to_user(actor=roles_setup["manager_a"], user=employee, role=admin_general, branch=branch_a)


def test_branch_manager_can_assign_operational_role_in_branch(client, roles_setup):
    employee = roles_setup["employee"]
    vendedor = roles_setup["vendedor"]
    branch_a = roles_setup["branch_a"]
    client.force_login(roles_setup["manager_a"])

    response = client.post(f"/accounts/users/{employee.pk}/roles/add/", {"role": vendedor.pk, "branch": branch_a.pk})

    assert response.status_code == 302
    assert UserRole.objects.filter(user=employee, role=vendedor, branch=branch_a, is_active=True).exists()


def test_branch_manager_cannot_assign_outside_branch(client, roles_setup):
    employee = roles_setup["employee"]
    vendedor = roles_setup["vendedor"]
    branch_b = roles_setup["branch_b"]
    client.force_login(roles_setup["manager_a"])

    response = client.post(f"/accounts/users/{employee.pk}/roles/add/", {"role": vendedor.pk, "branch": branch_b.pk})

    assert response.status_code == 302
    assert not UserRole.objects.filter(user=employee, role=vendedor, branch=branch_b).exists()

    with pytest.raises(PermissionDenied):
        assign_role_to_user(actor=roles_setup["manager_a"], user=employee, role=vendedor, branch=branch_b)


def test_branch_manager_cannot_remove_global_assignment(client, roles_setup):
    employee = roles_setup["employee"]
    auditor = roles_setup["auditor"]
    global_binding = UserRole.objects.create(user=employee, role=auditor)
    client.force_login(roles_setup["manager_a"])

    response = client.post(f"/accounts/users/{employee.pk}/roles/{global_binding.pk}/remove/")

    assert response.status_code == 302
    global_binding.refresh_from_db()
    assert global_binding.is_active


def test_branch_manager_cannot_remove_other_branch_binding(client, roles_setup):
    employee = roles_setup["employee"]
    vendedor = roles_setup["vendedor"]
    branch_b = roles_setup["branch_b"]
    other_branch_binding = UserRole.objects.create(user=employee, role=vendedor, branch=branch_b)
    client.force_login(roles_setup["manager_a"])

    response = client.post(f"/accounts/users/{employee.pk}/roles/{other_branch_binding.pk}/remove/")

    assert response.status_code == 302
    other_branch_binding.refresh_from_db()
    assert other_branch_binding.is_active


def test_branch_manager_cannot_remove_privileged_binding(client, roles_setup):
    employee = roles_setup["employee"]
    admin_general = roles_setup["admin_general"]
    branch_a = roles_setup["branch_a"]
    privileged_binding = UserRole.objects.create(user=employee, role=admin_general, branch=branch_a)
    client.force_login(roles_setup["manager_a"])

    response = client.post(f"/accounts/users/{employee.pk}/roles/{privileged_binding.pk}/remove/")

    assert response.status_code == 302
    privileged_binding.refresh_from_db()
    assert privileged_binding.is_active

    with pytest.raises(PermissionDenied):
        remove_user_role(actor=roles_setup["manager_a"], user_role=privileged_binding)


def test_branch_manager_does_not_see_out_of_scope_assignments(client, roles_setup):
    employee = roles_setup["employee"]
    vendedor = roles_setup["vendedor"]
    auditor = roles_setup["auditor"]
    admin_general = roles_setup["admin_general"]
    branch_a = roles_setup["branch_a"]
    visible_binding = UserRole.objects.create(user=employee, role=vendedor, branch=branch_a)
    hidden_global_binding = UserRole.objects.create(user=employee, role=auditor)
    hidden_privileged_binding = UserRole.objects.create(user=employee, role=admin_general, branch=branch_a)
    client.force_login(roles_setup["manager_a"])

    response = client.get(f"/accounts/users/{employee.pk}/")
    assert response.status_code == 200
    content = response.content.decode()
    assert f"/roles/{visible_binding.pk}/remove/" in content
    assert f"/roles/{hidden_global_binding.pk}/remove/" not in content
    assert f"/roles/{hidden_privileged_binding.pk}/remove/" not in content


def test_global_assigner_keeps_global_operations(client, roles_setup):
    employee = roles_setup["employee"]
    auditor = roles_setup["auditor"]
    vendedor = roles_setup["vendedor"]
    branch_a = roles_setup["branch_a"]
    global_manager = roles_setup["global_manager"]
    client.force_login(global_manager)

    response = client.post(f"/accounts/users/{employee.pk}/roles/add/", {"role": auditor.pk})
    assert response.status_code == 302
    global_binding = UserRole.objects.get(user=employee, role=auditor)
    assert global_binding.is_active
    assert global_binding.branch is None

    response = client.post(f"/accounts/users/{employee.pk}/roles/add/", {"role": vendedor.pk, "branch": branch_a.pk})
    assert response.status_code == 302

    response = client.post(f"/accounts/users/{employee.pk}/roles/{global_binding.pk}/remove/")
    assert response.status_code == 302
    global_binding.refresh_from_db()
    assert not global_binding.is_active
