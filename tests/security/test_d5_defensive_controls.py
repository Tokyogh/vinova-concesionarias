"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for d5 defensive controls in the security domain.
"""

from __future__ import annotations


import pytest
from django.core.cache import cache
from django.test import Client, override_settings
from django.urls import reverse

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.security_center.models import SecurityPolicy
from tests.security.production_settings_probe import production_security_settings

SENSITIVE_URLS = [
    "/dashboard/vehicles/",
    "/dashboard/customers/",
    "/dashboard/inventory/",
    "/dashboard/sales/",
    "/dashboard/invoices/",
    "/dashboard/documents/",
    "/dashboard/reports/",
    "/dashboard/imports/",
    "/dashboard/audit/",
    "/dashboard/continuity/",
    "/dashboard/privacy/",
    "/dashboard/quality/",
    "/dashboard/security/",
    "/dashboard/integrations/",
    "/accounts/users/",
    "/accounts/users/new/",
    "/branches/",
    "/companies/",
    "/api/v1/vehicles/",
    "/api/v1/customers/",
]

MUTATING_URLS = [
    "customers_internal:create",
    "accounts:user_create",
]


@pytest.fixture(name="staff_ctx")
def staff_ctx_fixture(django_user_model):
    company = Company.objects.create(legal_name="Ctx S.A.", commercial_name="Ctx", ruc="1711111111001")
    branch = Branch.objects.create(company=company, name="Central", code="CEN", city="Quito")
    user = django_user_model.objects.create_user(
        username="d5_staff", email="d5_staff@example.com", password="Passw0rd!2345"
    )
    return {"user": user, "branch": branch}


def _add_role(user, *, code, permissions, branch=None):
    role = Role.objects.create(code=code, name=code)
    role.permissions.set(permissions)
    return UserRole.objects.create(user=user, role=role, branch=branch)


@pytest.mark.django_db
def test_session_and_csrf_cookie_flags(client, settings):
    assert settings.SESSION_COOKIE_HTTPONLY is True
    assert settings.SESSION_COOKIE_SAMESITE == "Lax"
    assert settings.CSRF_COOKIE_SAMESITE == "Lax"
    assert settings.SECURE_CONTENT_TYPE_NOSNIFF is True
    assert settings.X_FRAME_OPTIONS == "DENY"


def test_production_settings_hardcode_secure_cookies():
    production = production_security_settings()

    assert production["session_secure"] is True
    assert production["csrf_secure"] is True
    assert production["coop"] == "same-origin"
    assert production["save_every_request"] is True


@pytest.mark.django_db
def test_security_headers_are_hardened(client):
    response = client.get("/")
    assert response.status_code == 200

    csp = response.headers.get("Content-Security-Policy", "")
    assert csp
    script_src = [part for part in csp.split(";") if part.strip().startswith("script-src")]
    assert script_src
    assert "unsafe-inline" not in script_src[0]
    assert "unsafe-eval" not in script_src[0]
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp
    style_src = next(part.strip() for part in csp.split(";") if part.strip().startswith("style-src "))
    assert "unsafe-inline" not in style_src
    assert "'nonce-" in style_src
    assert "style-src-attr 'unsafe-inline'" in csp

    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "camera=()" in response.headers.get("Permissions-Policy", "")
    assert response.headers.get("Cross-Origin-Opener-Policy") == "same-origin"


@pytest.mark.django_db
def test_mutating_views_reject_requests_without_csrf_token(staff_ctx):
    user = staff_ctx["user"]
    _add_role(
        user,
        code="d5_csrf_role",
        permissions=[
            PermissionCode.objects.create(module="customers", code="customers.manage", name="manage"),
            PermissionCode.objects.create(module="dashboard", code="dashboard.view", name="dash"),
        ],
        branch=staff_ctx["branch"],
    )

    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(user)
    response = csrf_client.post(reverse("customers_internal:create"), {"first_name": "Robo"})

    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("path", SENSITIVE_URLS)
def test_sensitive_urls_are_denied_to_unauthenticated_requests(client, path):
    response = client.get(path)
    assert response.status_code in {302, 401, 403}, f"{path} devolvió {response.status_code}"


@pytest.mark.django_db
@pytest.mark.parametrize("path", SENSITIVE_URLS)
def test_sensitive_urls_are_denied_without_permissions(client, django_user_model, path):
    user = django_user_model.objects.create_user(
        username="d5_client_only", email="d5_client_only@example.com", password="Passw0rd!2345"
    )
    _add_role(user, code="d5_client_role", permissions=[], branch=None)
    client.force_login(user)

    response = client.get(path)

    assert response.status_code in {401, 403}, f"{path} devolvió {response.status_code}"


@pytest.mark.django_db
@pytest.mark.parametrize("name", MUTATING_URLS)
def test_mutating_views_require_permission(staff_ctx, client, name):
    client.force_login(staff_ctx["user"])
    response = client.post(reverse(name), {})

    assert response.status_code == 403


@pytest.mark.django_db
def test_login_is_throttled_after_policy_threshold(django_user_model, settings):
    django_user_model.objects.create_user(
        username="d5_victim", email="d5_victim@example.com", password="Passw0rd!2345"
    )
    policy = SecurityPolicy.current()
    policy.login_attempts_per_ip = 3
    policy.save(update_fields=["login_attempts_per_ip", "updated_at"])
    cache.clear()

    throttle_client = Client()
    for attempt in range(3):
        throttle_client.post(
            "/accounts/login/",
            {"username": "d5_victim", "password": "wrong-password"},
            REMOTE_ADDR="192.0.2.77",
        )

    blocked = throttle_client.post(
        "/accounts/login/",
        {"username": "d5_victim", "password": "Passw0rd!2345"},
        REMOTE_ADDR="192.0.2.77",
    )
    authenticated = throttle_client.get("/accounts/profile/", follow=False)

    assert blocked.status_code != 302
    assert authenticated.status_code == 302
    cache.clear()


@pytest.mark.django_db
def test_api_declares_throttle_rates_for_configured_scopes(settings):
    from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

    rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    assert {"anon", "user", "api_client"} <= set(rates)
    assert rates[AnonRateThrottle.scope]
    assert rates[UserRateThrottle.scope]


@pytest.mark.django_db
def test_api_returns_429_when_authenticated_rate_is_exhausted(staff_ctx, client, monkeypatch):
    from rest_framework import throttling as drf_throttling

    user = staff_ctx["user"]
    _add_role(
        user,
        code="d5_api_role",
        permissions=[
            PermissionCode.objects.create(module="vehicles", code="vehicles.view", name="view"),
            PermissionCode.objects.create(module="dashboard", code="dashboard.view", name="dash"),
        ],
        branch=staff_ctx["branch"],
    )
    # DRF congela las tasas en THROTTLE_RATES al importar; se fija una tasa baja
    # para poder verificar el 429 sin disparar 1200 peticiones reales.
    monkeypatch.setattr(
        drf_throttling.UserRateThrottle,
        "THROTTLE_RATES",
        {"anon": "60/hour", "user": "2/min", "api_client": "600/hour"},
        raising=False,
    )
    cache.clear()
    client.force_login(user)

    codes = [client.get("/api/v1/vehicles/").status_code for _ in range(3)]

    assert codes[0] == 200
    assert codes[-1] == 429
    cache.clear()


@pytest.mark.django_db
def test_search_filter_treats_sql_payload_as_plain_text(django_user_model, client):
    company = Company.objects.create(legal_name="Sql Co S.A.", commercial_name="SqlCo", ruc="1722222222001")
    branch = Branch.objects.create(company=company, name="Sql Branch", code="SQL", city="Quito")
    user = django_user_model.objects.create_user(
        username="d5_sql", email="d5_sql@example.com", password="Passw0rd!2345"
    )
    _add_role(
        user,
        code="d5_sql_role",
        permissions=[
            PermissionCode.objects.create(module="customers", code="customers.view", name="view"),
            PermissionCode.objects.create(module="dashboard", code="dashboard.view", name="dash"),
        ],
        branch=branch,
    )
    client.force_login(user)

    response = client.get("/dashboard/customers/", {"q": "' OR 1=1; DROP TABLE customers_customer;--"})

    assert response.status_code == 200


@pytest.mark.django_db
def test_script_payload_is_escaped_when_rendered(django_user_model, client):
    company = Company.objects.create(legal_name="Xss Co S.A.", commercial_name="XssCo", ruc="1733333333001")
    branch = Branch.objects.create(company=company, name="Xss Branch", code="XSS", city="Quito")
    user = django_user_model.objects.create_user(
        username="d5_xss", email="d5_xss@example.com", password="Passw0rd!2345"
    )
    _add_role(
        user,
        code="d5_xss_role",
        permissions=[
            PermissionCode.objects.create(module="customers", code="customers.view", name="view"),
            PermissionCode.objects.create(module="dashboard", code="dashboard.view", name="dash"),
        ],
        branch=branch,
    )

    from apps.customers.models import Customer

    Customer.objects.create(
        first_name="<script>alert('d5')</script>",
        last_name="</title><img src=x onerror=alert(1)>",
        identification_number="1799999999009",
        assigned_branch=branch,
        created_by=user,
    )
    client.force_login(user)

    response = client.get("/dashboard/customers/")

    assert response.status_code == 200
    body = response.content.decode(response.charset, errors="replace")
    assert "<script>alert('d5')</script>" not in body
    assert "onerror=alert(1)>" not in body
    assert "&lt;script&gt;" in body


@pytest.mark.django_db
@override_settings(VINOVA_MODULE_POST_SALES_ENABLED=False)
def test_post_sales_flag_off_blocks_get_and_post(staff_ctx, client):
    user = staff_ctx["user"]
    _add_role(
        user,
        code="d5_postventa_role",
        permissions=[
            PermissionCode.objects.create(module="post_sales", code="post_sales.view", name="view"),
            PermissionCode.objects.create(module="post_sales", code="post_sales.manage", name="manage"),
            PermissionCode.objects.create(module="dashboard", code="dashboard.view", name="dash"),
        ],
        branch=staff_ctx["branch"],
    )
    client.force_login(user)

    assert client.get("/dashboard/post-sales/").status_code == 404
    assert client.get("/dashboard/post-sales/new/").status_code == 404
    assert client.post("/dashboard/post-sales/new/", {}).status_code == 404
