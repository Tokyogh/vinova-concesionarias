"""ES: Este módulo especifica regresiones ejecutables para el dominio de ayuda.

EN: This module specifies executable regressions for the help center domain.

Contexto existente / Existing context:
Regression coverage for help center v022 in the help_center domain.
"""

from __future__ import annotations

import pytest
from django.core.management import call_command
from django.urls import resolve, reverse

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.audit.models import AuditLog
from apps.help_center.models import (
    HelpArticle,
    HelpCategory,
    HelpChecklist,
    UserChecklistProgress,
    UserHelpPreference,
)


def grant_permissions(user, codes, *, role_code="help-role"):
    role = Role.objects.create(code=f"{role_code}-{user.username}", name=f"Ayuda {user.username}", level=30)
    permissions = []
    for code in codes:
        permission, _ = PermissionCode.objects.get_or_create(
            code=code,
            defaults={"module": code.split(".", 1)[0], "name": code},
        )
        permissions.append(permission)
    role.permissions.set(permissions)
    UserRole.objects.create(user=user, role=role)
    return role


@pytest.mark.django_db
def test_seed_help_center_is_idempotent_and_complete():
    call_command("seed_help_center")
    first_counts = (HelpCategory.objects.count(), HelpArticle.objects.count(), HelpChecklist.objects.count())
    call_command("seed_help_center")

    assert first_counts == (9, 17, 9)
    assert (HelpCategory.objects.count(), HelpArticle.objects.count(), HelpChecklist.objects.count()) == first_counts
    assert HelpArticle.objects.filter(slug="manual-administrador-general", is_published=True).exists()
    assert HelpChecklist.objects.get(slug="puesta-en-marcha-administrador").items.count() == 7


@pytest.mark.django_db
def test_help_center_requires_specific_permission(client, django_user_model):
    user = django_user_model.objects.create_user(username="without-help", email="without-help@example.com", password="x")
    client.force_login(user)
    denied = client.get(reverse("help_center:home"))
    assert denied.status_code == 403

    grant_permissions(user, ["help.view"])
    allowed = client.get(reverse("help_center:home"))
    assert allowed.status_code == 200
    assert b"Centro de ayuda y capacitaci" in allowed.content


@pytest.mark.django_db
def test_search_does_not_expose_admin_manual_to_basic_user(client, django_user_model):
    call_command("seed_help_center")
    user = django_user_model.objects.create_user(username="basic-help", email="basic-help@example.com", password="x")
    grant_permissions(user, ["help.view", "dashboard.view"])
    client.force_login(user)

    response = client.get(reverse("help_center:search"), {"q": "administrador general"})

    assert response.status_code == 200
    assert b"Manual del administrador general" not in response.content
    article = HelpArticle.objects.get(slug="manual-administrador-general")
    detail = client.get(reverse("help_center:article", kwargs={"slug": article.slug}))
    assert detail.status_code == 404


@pytest.mark.django_db
def test_admin_can_read_and_print_role_manual(client, django_user_model):
    call_command("seed_help_center")
    user = django_user_model.objects.create_user(username="help-admin", email="help-admin@example.com", password="x")
    role = Role.objects.create(code="admin_general", name="Administrador general", level=5)
    role.permissions.set(
        [
            PermissionCode.objects.create(module="help", code="help.view", name="Ver ayuda"),
            PermissionCode.objects.create(
                module="accounts",
                code="accounts.manage_users",
                name="Gestionar usuarios",
            ),
        ]
    )
    UserRole.objects.create(user=user, role=role)
    client.force_login(user)

    detail = client.get(reverse("help_center:article", kwargs={"slug": "manual-administrador-general"}))
    printable = client.get(reverse("help_center:article_print", kwargs={"slug": "manual-administrador-general"}))

    assert detail.status_code == 200
    assert b"Manual del administrador general" in detail.content
    assert printable.status_code == 200
    assert b"Imprimir o guardar como PDF" in printable.content


@pytest.mark.django_db
def test_training_mode_shows_contextual_tip_on_real_route(client, django_user_model):
    call_command("seed_help_center")
    user = django_user_model.objects.create_user(username="vehicle-help", email="vehicle-help@example.com", password="x")
    grant_permissions(user, ["help.view", "vehicles.view"])
    UserHelpPreference.objects.create(user=user, training_mode=True)
    client.force_login(user)

    response = client.get(reverse("vehicles_internal:list"))

    assert response.status_code == 200
    assert b"Modo capacitaci" in response.content
    assert b"Creaci" in response.content
    assert b"Abrir gu\xc3\xada" in response.content


@pytest.mark.django_db
def test_training_mode_toggle_is_audited(client, django_user_model):
    user = django_user_model.objects.create_user(username="training-user", email="training-user@example.com", password="x")
    grant_permissions(user, ["help.view"])
    client.force_login(user)

    response = client.post(reverse("help_center:training_mode"), {"enabled": "1", "next": reverse("help_center:home")})

    assert response.status_code == 302
    assert UserHelpPreference.objects.get(user=user).training_mode is True
    assert AuditLog.objects.filter(user=user, action="help.training_mode.updated").exists()


@pytest.mark.django_db
def test_checklist_progress_is_private_per_user_and_audited(client, django_user_model):
    call_command("seed_help_center")
    first = django_user_model.objects.create_user(username="inventory-help", email="inventory-help@example.com", password="x")
    second = django_user_model.objects.create_user(username="inventory-help-2", email="inventory-help-2@example.com", password="x")
    grant_permissions(first, ["help.view", "inventory.view"])
    grant_permissions(second, ["help.view", "inventory.view"])
    checklist = HelpChecklist.objects.get(slug="control-diario-inventario")
    item = checklist.items.first()
    client.force_login(first)

    response = client.post(reverse("help_center:toggle_item", kwargs={"item_id": item.pk}))

    assert response.status_code == 302
    assert UserChecklistProgress.objects.filter(user=first, item=item).exists()
    assert not UserChecklistProgress.objects.filter(user=second, item=item).exists()
    assert AuditLog.objects.filter(user=first, action="help.checklist.updated").exists()

    second_toggle = client.post(reverse("help_center:toggle_item", kwargs={"item_id": item.pk}))
    assert second_toggle.status_code == 302
    assert not UserChecklistProgress.objects.filter(user=first, item=item).exists()


@pytest.mark.django_db
def test_seed_roles_grants_help_only_to_internal_roles():
    call_command("seed_roles")

    assert Role.objects.get(code="vendedor").permissions.filter(code="help.view").exists()
    assert Role.objects.get(code="auditor").permissions.filter(code="help.view").exists()
    assert Role.objects.get(code="admin_general").permissions.filter(code="help.manage").exists()
    assert not Role.objects.get(code="cliente").permissions.filter(code="help.view").exists()


@pytest.mark.django_db
def test_help_routes_resolve_and_sidebar_is_visible(client, django_user_model):
    assert resolve("/dashboard/help/").view_name == "help_center:home"
    assert resolve("/dashboard/help/search/").view_name == "help_center:search"

    user = django_user_model.objects.create_user(username="sidebar-help", email="sidebar-help@example.com", password="x")
    grant_permissions(user, ["help.view", "dashboard.view"])
    client.force_login(user)
    response = client.get(reverse("dashboard:staff_home"))
    assert response.status_code == 200
    assert b"Ayuda y capacitaci" in response.content

@pytest.mark.django_db
def test_all_seeded_context_routes_are_reversible():
    call_command("seed_help_center")
    route_names = set(HelpArticle.objects.exclude(route_name="").values_list("route_name", flat=True))
    for checklist in HelpChecklist.objects.prefetch_related("items"):
        route_names.update(item.route_name for item in checklist.items.all() if item.route_name)

    resolved_urls = {route_name: reverse(route_name) for route_name in route_names}

    assert len(resolved_urls) == 28
    assert resolved_urls["continuity:dashboard"] == "/dashboard/continuity/"
    assert resolved_urls["api_internal:dashboard"] == "/dashboard/integrations/"


@pytest.mark.django_db
def test_training_mode_rejects_external_next_url(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="training-redirect",
        email="training-redirect@example.com",
        password="x",
    )
    grant_permissions(user, ["help.view"])
    client.force_login(user)

    response = client.post(
        reverse("help_center:training_mode"),
        {"enabled": "1", "next": "https://attacker.example/redirect"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("help_center:home")
