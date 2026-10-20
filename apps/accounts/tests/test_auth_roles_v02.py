"""ES: Este módulo especifica regresiones ejecutables para el dominio de cuentas.

EN: This module specifies executable regressions for the accounts domain.

Contexto existente / Existing context:
Regression coverage for auth roles v02 in the accounts domain.
"""

import pytest

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.accounts.services import assign_role_to_user
from apps.branches.models import Branch
from apps.companies.models import Company


def make_branch():
    company = Company.objects.create(
        legal_name="Empresa Demo S.A.",
        commercial_name="Empresa Demo",
        ruc="1790000000001",
    )
    return Branch.objects.create(
        company=company,
        name="Sucursal Demo",
        code="SUC-DEMO",
        branch_type=Branch.BranchType.DEALERSHIP,
        city="Quito",
    )


@pytest.mark.django_db
def test_user_can_login_with_email(client, django_user_model):
    django_user_model.objects.create_user(username="ana", email="ana@example.com", password="VinovaTest2026*")
    response = client.post("/accounts/login/", {"username": "ana@example.com", "password": "VinovaTest2026*"})
    assert response.status_code == 302


@pytest.mark.django_db
def test_role_assignment_service_reactivates_operational_role_with_branch(django_user_model):
    actor = django_user_model.objects.create_superuser(username="admin", email="admin@example.com", password="x")
    user = django_user_model.objects.create_user(username="ana", email="ana@example.com", password="x")
    branch = make_branch()
    role = Role.objects.create(code="vendedor", name="Vendedor")
    user_role = UserRole.objects.create(user=user, role=role, branch=branch, is_active=False)

    assign_role_to_user(actor=actor, user=user, role=role, branch=branch)

    user_role.refresh_from_db()
    assert user_role.is_active is True


@pytest.mark.django_db
def test_operational_role_requires_branch_in_assignment_service(django_user_model):
    actor = django_user_model.objects.create_superuser(username="admin", email="admin2@example.com", password="x")
    user = django_user_model.objects.create_user(username="carlos", email="carlos@example.com", password="x")
    role = Role.objects.create(code="vendedor", name="Vendedor")

    with pytest.raises(ValueError, match="roles operativos requieren sucursal"):
        assign_role_to_user(actor=actor, user=user, role=role)


@pytest.mark.django_db
def test_global_role_can_be_assigned_without_branch(django_user_model):
    actor = django_user_model.objects.create_superuser(username="admin", email="admin3@example.com", password="x")
    user = django_user_model.objects.create_user(username="maria", email="maria@example.com", password="x")
    role = Role.objects.create(code="marketing", name="Marketing / catálogo")

    user_role = assign_role_to_user(actor=actor, user=user, role=role)

    assert user_role.branch is None
    assert user_role.is_active is True


@pytest.mark.django_db
def test_permission_code_from_multiple_roles(django_user_model):
    user = django_user_model.objects.create_user(username="ana", email="ana2@example.com", password="x")
    branch = make_branch()
    p1 = PermissionCode.objects.create(module="vehicles", code="vehicles.view", name="Ver vehículos")
    p2 = PermissionCode.objects.create(module="accounts", code="accounts.manage_users", name="Gestionar usuarios")
    role1 = Role.objects.create(code="vendedor", name="Vendedor")
    role2 = Role.objects.create(code="admin_sucursal", name="Administrador de sucursal")
    role1.permissions.add(p1)
    role2.permissions.add(p2)
    UserRole.objects.create(user=user, role=role1, branch=branch)
    UserRole.objects.create(user=user, role=role2, branch=branch)
    assert user.has_perm_code("vehicles.view")
    assert user.has_perm_code("accounts.manage_users")
