"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for d5 export authorization in the security domain.
"""

from __future__ import annotations

import pytest

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company

HTML_EXPORTS = [
    ("analytics_export", "/dashboard/analytics/export/", [("analytics", "analytics.view"), ("analytics", "analytics.export")]),
    ("audit_export", "/dashboard/audit/export/", [("audit", "audit.view"), ("audit", "audit.export")]),
    ("reports_export", "/dashboard/reports/sales/export/csv/", [("reports", "reports.view"), ("reports", "data.export")]),
    ("import_template", "/dashboard/imports/templates/vehicles/", [("imports", "imports.manage")]),
    ("leads_export", "/dashboard/leads/export/", [("leads", "leads.view"), ("leads", "leads.export")]),
]

API_EXPORTS = [
    ("bi_catalog", "/api/v1/bi/", [("analytics", "analytics.export")]),
    ("bi_dataset", "/api/v1/bi/sales/", [("analytics", "analytics.export")]),
    ("accounting_export", "/api/v1/integrations/accounting/export/", [("billing", "data.export")]),
]

HTML_IDS = [entry[0] for entry in HTML_EXPORTS]
API_IDS = [entry[0] for entry in API_EXPORTS]


def _permissions(required: list[tuple[str, str]]) -> list[PermissionCode]:
    return [
        PermissionCode.objects.get_or_create(code=code, defaults={"module": module, "name": code})[0]
        for module, code in required
    ]


def _branch_user(django_user_model, *, username, permissions):
    # ES: force_login no necesita una contraseña utilizable en estas pruebas.
    # EN: force_login does not need a usable password in these tests.
    company = Company.objects.create(
        legal_name="Vinova Export S.A.",
        commercial_name="Vinova",
        ruc="1799999999002",
    )
    branch = Branch.objects.create(company=company, name="Central", code="CT", city="Quito")
    user = django_user_model.objects.create_user(
        username=username, email=f"{username}@example.com", password=None
    )
    if permissions:
        role = Role.objects.create(code=f"role_{username}", name=username)
        role.permissions.set(permissions)
        UserRole.objects.create(user=user, role=role, branch=branch)
    return user


@pytest.mark.django_db
@pytest.mark.parametrize("name,path,required", HTML_EXPORTS, ids=HTML_IDS)
def test_html_exports_redirect_anonymous_users_to_login(client, name, path, required):
    response = client.get(path)

    assert response.status_code in {301, 302}, f"{path} devolvió {response.status_code}"
    assert "login" in response["Location"]


@pytest.mark.django_db
@pytest.mark.parametrize("name,path,required", HTML_EXPORTS, ids=HTML_IDS)
def test_html_exports_deny_authenticated_user_without_permissions(django_user_model, client, name, path, required):
    user = _branch_user(django_user_model, username=f"no_perm_{name}", permissions=[])
    client.force_login(user)

    response = client.get(path)

    assert response.status_code in {401, 403}, f"{path} devolvió {response.status_code}"


@pytest.mark.django_db
@pytest.mark.parametrize("name,path,required", HTML_EXPORTS, ids=HTML_IDS)
def test_html_exports_deny_user_with_only_the_module_permission(django_user_model, client, name, path, required):
    if len(required) < 2:
        pytest.skip("este endpoint exige un único permiso")
    module_permission = _permissions([required[0]])[0]
    user = _branch_user(django_user_model, username=f"view_only_{name}", permissions=[module_permission])
    client.force_login(user)

    assert client.get(path).status_code == 403, f"{path} debió denegar"


@pytest.mark.django_db
@pytest.mark.parametrize("name,path,required", HTML_EXPORTS, ids=HTML_IDS)
def test_html_exports_allow_holder_of_all_required_permissions(django_user_model, client, name, path, required):
    permissions = _permissions(required)
    user = _branch_user(django_user_model, username=f"with_perm_{name}", permissions=permissions)
    client.force_login(user)

    response = client.get(path)

    assert response.status_code == 200, f"{path} devolvió {response.status_code}"


@pytest.mark.django_db
@pytest.mark.parametrize("name,path,required", API_EXPORTS, ids=API_IDS)
def test_api_exports_reject_anonymous_requests(client, name, path, required):
    assert client.get(path).status_code in {401, 403}, path
    assert client.post(path, {}, content_type="application/json").status_code in {401, 403}, path


@pytest.mark.django_db
@pytest.mark.parametrize("name,path,required", API_EXPORTS, ids=API_IDS)
def test_api_exports_deny_authenticated_user_without_permissions(django_user_model, client, name, path, required):
    user = _branch_user(django_user_model, username=f"api_no_perm_{name}", permissions=[])
    client.force_login(user)

    response = client.get(path)

    assert response.status_code in {401, 403}, f"{path} devolvió {response.status_code}"


@pytest.mark.django_db
@pytest.mark.parametrize("name,path,required", API_EXPORTS, ids=API_IDS)
def test_api_exports_allow_holder_of_the_matching_permission(django_user_model, client, name, path, required):
    permissions = [PermissionCode.objects.get_or_create(code=code, defaults={"module": module, "name": code})[0] for module, code in required]
    user = _branch_user(django_user_model, username=f"api_with_perm_{name}", permissions=permissions)
    client.force_login(user)

    response = client.get(path)

    assert response.status_code == 200, f"{path} devolvió {response.status_code}"


@pytest.mark.django_db
def test_export_permissions_are_revoked_with_the_role(django_user_model, client):
    permission = PermissionCode.objects.get_or_create(
        code="analytics.export", defaults={"module": "analytics", "name": "analytics.export"}
    )[0]
    user = _branch_user(django_user_model, username="bi_revoked", permissions=[permission])
    client.force_login(user)
    assert client.get("/api/v1/bi/sales/").status_code == 200

    user.user_roles.all().delete()

    assert client.get("/api/v1/bi/sales/").status_code == 403
    assert client.get("/dashboard/analytics/export/").status_code == 403


@pytest.mark.django_db
def test_reports_view_permission_does_not_grant_export(django_user_model, client):
    permission = PermissionCode.objects.get_or_create(
        code="reports.view", defaults={"module": "reports", "name": "reports.view"}
    )[0]
    user = _branch_user(django_user_model, username="reports_viewer", permissions=[permission])
    client.force_login(user)

    assert client.get("/dashboard/reports/").status_code == 200
    assert client.get("/dashboard/reports/sales/export/csv/").status_code == 403
