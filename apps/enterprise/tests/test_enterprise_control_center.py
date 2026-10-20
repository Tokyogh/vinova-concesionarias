"""ES: Este módulo especifica regresiones ejecutables para el dominio de configuración empresarial.

EN: This module specifies executable regressions for the enterprise domain.

Contexto existente / Existing context:
Regression coverage for enterprise control center in the enterprise domain.
"""

import pytest

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.companies.models import Company
from apps.enterprise.models import ApprovalPolicy, CompanyPublicSettings
from apps.enterprise.services import ensure_default_approval_policies


@pytest.fixture
def enterprise_admin(django_user_model):
    user = django_user_model.objects.create_user(username="enterpriseadmin", email="enterpriseadmin@example.com", password="x")
    perms = {}
    for code in ["dashboard.view", "enterprise.manage", "sri.manage", "approvals.manage"]:
        perms[code], _ = PermissionCode.objects.get_or_create(module=code.split(".")[0], code=code, defaults={"name": code})
    role = Role.objects.create(code="admin_general_v014", name="Administrador general v0.14", level=5)
    role.permissions.set(perms.values())
    UserRole.objects.create(user=user, role=role)
    return user


@pytest.fixture
def company():
    return Company.objects.create(legal_name="Vinova Demo Motors S.A.", commercial_name="Vinova Demo", ruc="1799999999001", is_active=True)


@pytest.mark.django_db
def test_anonymous_user_is_redirected_from_enterprise_center(client, company):
    response = client.get("/dashboard/company/")
    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/")


@pytest.mark.django_db
def test_common_user_cannot_access_enterprise_center(client, django_user_model, company):
    user = django_user_model.objects.create_user(username="clientecc", email="clientecc@example.com", password="x")
    client.force_login(user)
    response = client.get("/dashboard/company/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_enterprise_admin_can_access_center_and_default_policies(client, enterprise_admin, company):
    client.force_login(enterprise_admin)
    response = client.get("/dashboard/company/")
    assert response.status_code == 200
    assert "Centro de configuración empresarial".encode() in response.content
    assert CompanyPublicSettings.objects.filter(company=company).exists()
    assert ApprovalPolicy.objects.filter(company=company).count() == len(ApprovalPolicy.Action.choices)


@pytest.mark.django_db
def test_approval_policy_threshold_logic(company):
    policies = ensure_default_approval_policies(company=company)
    discount = policies.get(action=ApprovalPolicy.Action.DISCOUNT)
    assert discount.requires_approval_for(percent=11)
    assert not discount.requires_approval_for(percent=5)
