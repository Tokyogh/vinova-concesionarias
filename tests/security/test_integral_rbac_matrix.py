"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Reusable contract tests for Vinova's canonical role and branch matrix.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.management.commands.seed_roles import (
    PERMISSIONS,
    ROLE_DEFINITIONS,
    ROLE_PERMISSION_MAP,
)
from apps.accounts.models import Role, UserRole
from apps.accounts.scopes import accessible_branch_ids, assignable_role_queryset_for
from apps.branches.models import Branch
from apps.companies.models import Company


ALL_PERMISSION_CODES = {permission[1] for permission in PERMISSIONS}


def expected_permissions(role_code: str) -> set[str]:
    if role_code in {"superadmin", "admin_general"}:
        return ALL_PERMISSION_CODES
    return set(ROLE_PERMISSION_MAP[role_code])


@pytest.fixture(name="branches")
def branches_fixture():
    company = Company.objects.create(
        legal_name="Matriz RBAC S.A.",
        commercial_name="Matriz RBAC",
        ruc="1799999999002",
    )
    return (
        Branch.objects.create(company=company, name="RBAC Norte", code="RB-N", city="Quito"),
        Branch.objects.create(company=company, name="RBAC Sur", code="RB-S", city="Guayaquil"),
    )


@pytest.mark.django_db
@pytest.mark.parametrize("role_code", tuple(ROLE_DEFINITIONS))
def test_seeded_role_has_exact_permission_contract(django_user_model, role_code):
    """Every omitted permission is denied; no role may gain permission by drift."""
    call_command("seed_roles", verbosity=0)
    role = Role.objects.get(code=role_code)
    user = django_user_model.objects.create_user(
        username=f"matrix_{role_code}",
        email=f"matrix_{role_code}@example.invalid",
        password="unused-test-password",
    )
    UserRole.objects.create(user=user, role=role)

    expected = expected_permissions(role_code)
    actual = set(role.permissions.values_list("code", flat=True))

    assert actual == expected
    for permission_code in ALL_PERMISSION_CODES:
        assert user.has_perm_code(permission_code) is (permission_code in expected)


@pytest.mark.django_db
def test_branch_assignment_never_grants_foreign_or_global_scope(django_user_model, branches):
    call_command("seed_roles", verbosity=0)
    own_branch, foreign_branch = branches
    role = Role.objects.get(code="vendedor")
    user = django_user_model.objects.create_user(username="matrix_branch", email="branch@example.invalid")
    UserRole.objects.create(user=user, role=role, branch=own_branch)

    assert user.has_perm_code("sales.quote", branch=own_branch)
    assert not user.has_perm_code("sales.quote", branch=foreign_branch)
    assert accessible_branch_ids(user, permission_codes=("sales.quote",)) == (own_branch.pk,)
    assert accessible_branch_ids(user, permission_codes=("accounts.manage_users",)) == ()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("assignment_state", "starts_delta", "expires_delta"),
    (
        (False, None, None),
        (True, timedelta(hours=1), None),
        (True, None, timedelta(seconds=-1)),
    ),
)
def test_revoked_future_and_expired_assignments_deny_permission(
    django_user_model,
    branches,
    assignment_state,
    starts_delta,
    expires_delta,
):
    call_command("seed_roles", verbosity=0)
    user = django_user_model.objects.create_user(username=f"matrix_window_{starts_delta}_{expires_delta}")
    now = timezone.now()
    UserRole.objects.create(
        user=user,
        role=Role.objects.get(code="vendedor"),
        branch=branches[0],
        is_active=assignment_state,
        starts_at=now + starts_delta if starts_delta else None,
        expires_at=now + expires_delta if expires_delta else None,
    )

    assert not user.has_perm_code("sales.quote", branch=branches[0])
    assert accessible_branch_ids(user, permission_codes=("sales.quote",)) == ()


@pytest.mark.django_db
@pytest.mark.parametrize("is_superuser", (False, True))
def test_inactive_account_has_no_domain_permission_or_scope(
    django_user_model,
    branches,
    is_superuser,
):
    call_command("seed_roles", verbosity=0)
    user = django_user_model.objects.create_user(
        username=f"matrix_inactive_{is_superuser}",
        is_active=False,
        is_superuser=is_superuser,
    )
    UserRole.objects.create(user=user, role=Role.objects.get(code="admin_general"))

    assert not user.has_perm_code("accounts.assign_roles")
    assert not user.active_role_assignments().exists()
    assert accessible_branch_ids(user, permission_codes=("accounts.assign_roles",)) == ()
    assert not assignable_role_queryset_for(user).exists()


@pytest.mark.django_db
def test_inactive_role_revokes_all_permissions(django_user_model):
    call_command("seed_roles", verbosity=0)
    role = Role.objects.get(code="admin_general")
    user = django_user_model.objects.create_user(username="matrix_inactive_role")
    UserRole.objects.create(user=user, role=role)
    role.is_active = False
    role.save(update_fields=["is_active", "updated_at"])

    assert not user.has_perm_code("accounts.assign_roles")
    assert accessible_branch_ids(user, permission_codes=("accounts.assign_roles",)) == ()
