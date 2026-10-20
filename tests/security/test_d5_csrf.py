"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for d5 csrf in the security domain.
"""

from __future__ import annotations

import pytest

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company

MUTATING_ENDPOINTS = [
    ("/dashboard/customers/new/", "customers"),
    ("/dashboard/inventory/new/", "inventory"),
    ("/dashboard/sales/new/", "sales"),
    ("/dashboard/imports/new/", "imports"),
    ("/dashboard/documents/upload/", "documents"),
    ("/accounts/users/new/", "accounts"),
    ("/branches/new/", "branches"),
    ("/dashboard/notifications/compose/", "notifications"),
    ("/dashboard/privacy/requests/new/", "privacy"),
    ("/dashboard/continuity/backups/create/", "continuity"),
    ("/api/v1/customers/", "customers"),
    ("/api/v1/vehicles/", "vehicles"),
]

IDS = [path for path, _ in MUTATING_ENDPOINTS]


@pytest.fixture(name="broad_staff")
def broad_staff_fixture(django_user_model):
    # ES: force_login no necesita una contraseña utilizable en estas pruebas.
    # EN: force_login does not need a usable password in these tests.
    company = Company.objects.create(
        legal_name="Vinova CSRF S.A.",
        commercial_name="Vinova",
        ruc="1799999999004",
    )
    branch = Branch.objects.create(company=company, name="Central", code="CS", city="Quito")
    user = django_user_model.objects.create_user(
        username="d5_csrf", email="d5_csrf@example.com", password=None
    )
    role = Role.objects.create(code="role_d5_csrf", name="d5 csrf")
    role.permissions.set(PermissionCode.objects.all())
    UserRole.objects.create(user=user, role=role, branch=branch)
    return user


@pytest.mark.django_db
@pytest.mark.parametrize("path,module", MUTATING_ENDPOINTS, ids=IDS)
def test_mutating_endpoints_reject_requests_without_csrf_token(broad_staff, path, module):
    from django.test import Client

    client = Client(enforce_csrf_checks=True)
    client.force_login(broad_staff)

    response = client.post(path, {"dummy": "1"}, content_type="application/x-www-form-urlencoded")

    assert response.status_code == 403, f"{path} aceptó un POST sin token CSRF ({response.status_code})"


@pytest.mark.django_db
@pytest.mark.parametrize("path,module", MUTATING_ENDPOINTS, ids=IDS)
def test_mutating_endpoints_redirect_anonymous_posts(broad_staff, path, module):
    from django.test import Client

    client = Client(enforce_csrf_checks=True)

    response = client.post(path, {"dummy": "1"}, content_type="application/x-www-form-urlencoded")

    assert response.status_code in {302, 401, 403}, f"{path} devolvió {response.status_code}"


@pytest.mark.django_db
def test_csrf_cookie_is_not_marked_httponly(broad_staff):
    from django.test import Client

    client = Client(enforce_csrf_checks=True)
    client.force_login(broad_staff)
    client.get("/accounts/profile/")

    cookie = client.cookies.get("csrftoken")
    assert cookie is not None, "no se emitió cookie CSRF"
    assert not cookie["httponly"]
