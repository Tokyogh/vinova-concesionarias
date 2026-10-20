"""ES: Este módulo especifica regresiones ejecutables para el dominio de paneles.

EN: This module specifies executable regressions for the dashboard domain.

Contexto existente / Existing context:
Regression coverage for tests in the dashboard domain.
"""

import json
import re

import pytest

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.dashboard.services import dashboard_manifest_for_user, dashboard_profile_for_user


def assign_role(user, *, code, permission_codes):
    permissions = [
        PermissionCode.objects.create(module=value.split(".")[0], code=value, name=value)
        for value in permission_codes
    ]
    role = Role.objects.create(code=code, name=code.replace("_", " ").title())
    role.permissions.add(*permissions)
    UserRole.objects.create(user=user, role=role)
    return role


@pytest.mark.django_db
def test_public_home_is_available_without_login(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Concesionaria automotriz" in response.content
    assert b"Usuarios y roles" not in response.content


def _public_navigation(response):
    html = response.content.decode()
    match = re.search(r'<nav class="public-nav".*?</nav>', html, re.DOTALL)
    assert match is not None
    return match.group()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("path", "active_label"),
    (
        ("/vehicles/", "Vehículos"),
        ("/servicios/", "Servicios"),
        ("/nosotros/", "Nosotros"),
        ("/leads/request/", "Contacto"),
    ),
)
def test_public_navigation_marks_only_the_resolved_section(client, path, active_label):
    navigation = _public_navigation(client.get(path))

    assert navigation.count('aria-current="page"') == 1
    assert f'aria-current="page">{active_label}</a>' in navigation


@pytest.mark.django_db
def test_public_home_does_not_mark_a_navigation_section(client):
    navigation = _public_navigation(client.get("/"))

    assert 'aria-current="page"' not in navigation


@pytest.mark.django_db
def test_authenticated_staff_user_can_open_public_home_without_losing_session(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="staff-public-home",
        email="staff-public-home@example.com",
        password="x",
        is_staff=True,
    )
    assign_role(user, code="staff_public_home", permission_codes=("dashboard.view",))
    client.force_login(user)

    response = client.get("/")

    assert response.status_code == 200
    assert response.context["user"] == user
    assert b"Panel interno" in response.content
    assert b"Ingresar" not in response.content


@pytest.mark.django_db
def test_internal_dashboard_requires_login(client):
    response = client.get("/dashboard/")
    assert response.status_code == 302
    assert "/accounts/login/" in response.headers["Location"]


@pytest.mark.django_db
def test_common_user_dashboard_redirects_to_profile(client, django_user_model):
    user = django_user_model.objects.create_user(username="cliente", email="cliente@example.com", password="x")
    client.force_login(user)
    response = client.get("/dashboard/")
    assert response.status_code == 302
    assert response.headers["Location"] == "/accounts/profile/"


@pytest.mark.django_db
def test_role_router_sends_seller_to_seller_dashboard(client, django_user_model):
    user = django_user_model.objects.create_user(username="seller", email="seller@example.com", password="x")
    perms = []
    for code in ["dashboard.view", "sales.quote", "sales.reserve", "customers.view", "vehicles.view"]:
        module = code.split(".")[0]
        perms.append(PermissionCode.objects.create(module=module, code=code, name=code))
    role = Role.objects.create(code="vendedor", name="Vendedor")
    role.permissions.add(*perms)
    UserRole.objects.create(user=user, role=role)
    client.force_login(user)
    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert b"Ventas y atenci" in response.content
    assert b"/dashboard/seller/" in response.content
    response = client.get("/dashboard/seller/")
    assert response.status_code == 200
    assert b"Dashboard vendedor" in response.content
    assert b"Usuarios y roles" not in response.content


@pytest.mark.django_db
def test_admin_dashboard_exposes_staff_management(client, django_user_model):
    user = django_user_model.objects.create_user(username="admin", email="admin@example.com", password="x")
    perms = []
    for code in ["dashboard.view", "accounts.manage_users", "companies.manage", "branches.manage"]:
        module = code.split(".")[0]
        perms.append(PermissionCode.objects.create(module=module, code=code, name=code))
    role = Role.objects.create(code="admin_general", name="Administrador general")
    role.permissions.add(*perms)
    UserRole.objects.create(user=user, role=role)
    client.force_login(user)
    assert dashboard_profile_for_user(user).code == "admin"
    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert b"Administraci" in response.content
    assert b"Usuarios y roles" in response.content
    response = client.get("/dashboard/admin/")
    assert response.status_code == 200
    assert b"Dashboard administrador" in response.content


@pytest.mark.django_db
def test_common_user_profile_does_not_expose_staff_navigation(client, django_user_model):
    user = django_user_model.objects.create_user(username="cliente", email="cliente2@example.com", password="x")
    client.force_login(user)
    response = client.get("/accounts/profile/")
    assert response.status_code == 200
    assert b"Usuarios y roles" not in response.content
    assert b"Empresas" not in response.content
    assert b"Panel interno" not in response.content


@pytest.mark.django_db
def test_custom_role_profile_and_widgets_come_from_real_permissions(django_user_model):
    user = django_user_model.objects.create_user(username="custom-stock", email="stock@example.com", password="x")
    assign_role(
        user,
        code="operacion_personalizada",
        permission_codes=("dashboard.view", "inventory.view"),
    )

    manifest = dashboard_manifest_for_user(user)

    assert manifest.profile.code == "inventory"
    assert [widget.key for widget in manifest.widgets] == ["inventory", "tasks", "activity"]
    assert manifest.actions == ()


@pytest.mark.django_db
def test_dashboard_preferences_cannot_restore_unauthorized_content(django_user_model):
    user = django_user_model.objects.create_user(username="seller-safe", email="seller-safe@example.com", password="x")
    assign_role(
        user,
        code="vendedor",
        permission_codes=("dashboard.view", "sales.quote", "customers.view"),
    )

    manifest = dashboard_manifest_for_user(
        user,
        {
            "widget_order": ["inventory", "activity", "sales"],
            "action_order": ["new_invoice", "new_quote"],
        },
    )

    assert [widget.key for widget in manifest.widgets] == ["activity", "sales", "customers", "tasks"]
    assert [action["key"] for action in manifest.actions] == ["new_quote"]


@pytest.mark.django_db
def test_dashboard_preferences_endpoint_sanitizes_keys(client, django_user_model):
    user = django_user_model.objects.create_user(username="seller-prefs", email="seller-prefs@example.com", password="x")
    assign_role(
        user,
        code="vendedor",
        permission_codes=("dashboard.view", "sales.quote"),
    )
    client.force_login(user)

    response = client.post(
        "/dashboard/preferences/",
        data=json.dumps({
            "widget_order": ["activity", "inventory", "activity", "sales"],
            "action_order": ["new_invoice", "new_quote", "new_quote"],
        }),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json() == {
        "widget_order": ["activity", "sales"],
        "action_order": ["new_quote"],
    }
