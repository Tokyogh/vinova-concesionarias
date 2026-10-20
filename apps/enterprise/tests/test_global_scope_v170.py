"""ES: Este módulo especifica regresiones ejecutables para el dominio de configuración empresarial.

EN: This module specifies executable regressions for the enterprise domain.

Contexto existente / Existing context:
Regression coverage for global scope v170 in the enterprise domain.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.audit.models import AuditLog
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.enterprise.models import CompanyPublicSettings
from apps.sri_integration.selectors import get_or_create_sri_configuration


pytestmark = pytest.mark.django_db


def make_enterprise_user(django_user_model, *, branch=None):
    permissions = [
        PermissionCode.objects.create(module=module, code=code, name=code)
        for module, code in (
            ("enterprise", "enterprise.manage"),
            ("sri", "sri.manage"),
        )
    ]
    role = Role.objects.create(code=f"enterprise-global-{branch is None}", name="Enterprise manager")
    role.permissions.set(permissions)
    user = django_user_model.objects.create_user(
        username=f"enterprise-global-{branch is None}",
        email=f"enterprise-global-{branch is None}@example.com",
        password="test12345",
    )
    UserRole.objects.create(user=user, role=role, branch=branch)
    return user


@pytest.fixture
def enterprise_context(django_user_model):
    company = Company.objects.create(
        legal_name="Enterprise Scope SA",
        commercial_name="Enterprise Scope",
        ruc="1799999999009",
    )
    branch = Branch.objects.create(company=company, name="Principal", code="ENT-A", city="Quito")
    public_settings = CompanyPublicSettings.objects.create(company=company)
    sri_config = get_or_create_sri_configuration(company)
    return company, branch, public_settings, sri_config


def test_branch_scoped_enterprise_role_cannot_access_global_configuration(
    client,
    django_user_model,
    enterprise_context,
):
    _, branch, _, _ = enterprise_context
    user = make_enterprise_user(django_user_model, branch=branch)
    client.force_login(user)

    assert client.get(reverse("enterprise:home")).status_code == 403
    assert client.get(reverse("sri_integration:configuration")).status_code == 403
    assert client.get("/api/company-public-settings/").status_code == 403
    assert client.get("/api/sri-configurations/").status_code == 403


def test_global_enterprise_api_is_audited_and_sri_api_is_read_only(
    client,
    django_user_model,
    enterprise_context,
):
    _, _, public_settings, sri_config = enterprise_context
    user = make_enterprise_user(django_user_model)
    client.force_login(user)

    response = client.patch(
        f"/api/company-public-settings/{public_settings.pk}/",
        {"footer_text": "Pie actualizado"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert AuditLog.objects.filter(
        action="enterprise.public_settings.api_update",
        object_id=str(public_settings.pk),
        user=user,
    ).exists()
    assert client.post("/api/company-public-settings/", {}).status_code == 405
    assert client.get(f"/api/sri-configurations/{sri_config.pk}/").status_code == 200
    assert client.post("/api/sri-configurations/", {}).status_code == 405
