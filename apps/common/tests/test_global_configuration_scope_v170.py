"""ES: Este módulo especifica regresiones ejecutables para el dominio de infraestructura compartida.

EN: This module specifies executable regressions for the common domain.

Contexto existente / Existing context:
Regression coverage for global configuration scope v170 in the common domain.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.audit.models import AuditLog
from apps.branches.models import Branch
from apps.companies.models import Company


pytestmark = pytest.mark.django_db


def configuration_context(django_user_model, *, global_scope):
    company = Company.objects.create(
        legal_name="Global Configuration SA",
        commercial_name="Global Configuration",
        ruc="1799999999007",
    )
    branch = Branch.objects.create(
        company=company,
        name="Principal",
        code="GLOBAL-CONFIG",
        branch_type=Branch.BranchType.DEALERSHIP,
        city="Quito",
    )
    permissions = [
        PermissionCode.objects.create(module=module, code=code, name=code)
        for module, code in (
            ("companies", "companies.manage"),
            ("branches", "branches.manage"),
        )
    ]
    role = Role.objects.create(code=f"configuration-{global_scope}", name="Configuration manager")
    role.permissions.set(permissions)
    user = django_user_model.objects.create_user(
        username=f"configuration-{global_scope}",
        email=f"configuration-{global_scope}@example.com",
        password="test12345",
    )
    UserRole.objects.create(user=user, role=role, branch=None if global_scope else branch)
    return user, company, branch


def test_branch_scoped_configuration_role_cannot_access_global_resources(client, django_user_model):
    user, _, _ = configuration_context(django_user_model, global_scope=False)
    client.force_login(user)

    assert client.get(reverse("companies:list")).status_code == 403
    assert client.get(reverse("branches:list")).status_code == 403
    assert client.get("/api/companies/").status_code == 403
    assert client.get("/api/branches/").status_code == 403


def test_global_configuration_api_updates_through_audited_services(client, django_user_model):
    user, company, branch = configuration_context(django_user_model, global_scope=True)
    client.force_login(user)

    company_response = client.patch(
        f"/api/companies/{company.pk}/",
        {"commercial_name": "Global Configuration Updated"},
        content_type="application/json",
    )
    branch_response = client.patch(
        f"/api/branches/{branch.pk}/",
        {"city": "Guayaquil"},
        content_type="application/json",
    )

    assert company_response.status_code == 200
    assert branch_response.status_code == 200
    assert AuditLog.objects.filter(action="companies.company.update", object_id=str(company.pk), user=user).exists()
    assert AuditLog.objects.filter(action="branches.branch.update", object_id=str(branch.pk), user=user).exists()
    assert client.delete(f"/api/companies/{company.pk}/").status_code == 405
    assert client.delete(f"/api/branches/{branch.pk}/").status_code == 405
