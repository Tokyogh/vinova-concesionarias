"""ES: Este módulo especifica regresiones ejecutables para el dominio de infraestructura compartida.

EN: This module specifies executable regressions for the common domain.

Contexto existente / Existing context:
Regression coverage for assist in the common domain.
"""

from types import SimpleNamespace

import pytest
from django.urls import reverse

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.common.assist import ALLOW_PERMISSION_CODES, ASSIST_INTENTS, assist_response_for_user
from apps.common.navigation import ALL_DESTINATIONS


def _user(**permissions):
    values = {"has_perm_code": lambda code: False}
    values.update(permissions)
    return SimpleNamespace(**values)


def test_assist_returns_real_authorized_document_deep_link():
    response = assist_response_for_user(
        _user(can_manage_documents=True),
        "¿Dónde puedo registrar documentos?",
    )

    assert response["results"][0]["key"] == "assist:upload_document"
    assert response["results"][0]["url"] == reverse("documents_internal:create")
    assert response["results"][0]["kind"] == "action"


def test_assist_explains_restricted_intent_without_exposing_route():
    response = assist_response_for_user(_user(), "registrar documentos")

    assert response["results"] == []
    assert "no tiene acceso" in response["answer"]
    assert reverse("documents_internal:create") not in response["answer"]


def test_assist_keeps_view_destination_but_hides_restricted_create_action():
    response = assist_response_for_user(
        _user(can_view_documents=True, can_manage_documents=False),
        "registrar documentos",
    )

    urls = {item["url"] for item in response["results"]}
    assert reverse("documents_internal:list") in urls
    assert reverse("documents_internal:create") not in urls
    assert "permisos adicionales" in response["answer"]


def test_assist_permission_snapshot_covers_every_registered_allow_rule():
    registered = {item.allow for item in ALL_DESTINATIONS.values() if item.allow}
    registered.update(intent.allow for intent in ASSIST_INTENTS)
    assert registered <= ALLOW_PERMISSION_CODES.keys()


def test_assist_safe_filter_is_static_and_registry_has_no_destructive_actions():
    response = assist_response_for_user(_user(can_view_leads=True), "seguimientos vencidos")

    assert response["results"][0]["url"].endswith("?overdue=on")
    forbidden = ("delete", "archive", "void", "remove")
    assert not any(word in intent.key.lower() for intent in ASSIST_INTENTS for word in forbidden)


@pytest.mark.django_db
def test_assist_endpoint_requires_internal_access_and_returns_json(client, django_user_model):
    common = django_user_model.objects.create_user(username="assist-common", password="StrongPass-2026!")
    client.force_login(common)
    assert client.get(reverse("dashboard:assist"), {"q": "ayuda"}).status_code == 403

    admin = django_user_model.objects.create_superuser(
        username="assist-admin", email="assist@example.com", password="StrongPass-2026!"
    )
    client.force_login(admin)
    response = client.get(reverse("dashboard:assist"), {"q": "registrar documentos"})

    assert response.status_code == 200
    assert response.json()["results"][0]["url"] == reverse("documents_internal:create")


@pytest.mark.django_db
def test_assist_resolves_all_permissions_in_one_query(django_assert_num_queries, django_user_model):
    permission = PermissionCode.objects.create(
        module="documents", code="documents.manage", name="Gestionar documentos"
    )
    role = Role.objects.create(code="assist_documents", name="Assist documentos")
    role.permissions.add(permission)
    user = django_user_model.objects.create_user(
        username="assist-scoped", email="assist-scoped@example.com", password="StrongPass-2026!"
    )
    UserRole.objects.create(user=user, role=role)

    with django_assert_num_queries(1):
        response = assist_response_for_user(user, "registrar documentos")

    assert response["results"][0]["key"] == "assist:upload_document"
