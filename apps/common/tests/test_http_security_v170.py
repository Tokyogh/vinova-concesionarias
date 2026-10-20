"""ES: Este módulo especifica regresiones ejecutables para el dominio de infraestructura compartida.

EN: This module specifies executable regressions for the common domain.

Contexto existente / Existing context:
Regression coverage for http security v170 in the common domain.
"""

import pytest
from django.test import RequestFactory
from django.urls import reverse

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.common.http import safe_next_url


def test_safe_next_url_rejects_external_and_scheme_relative_targets():
    request = RequestFactory().post("/action/", HTTP_HOST="testserver")

    assert safe_next_url(request, "https://evil.example/phish", "/fallback/") == "/fallback/"
    assert safe_next_url(request, "//evil.example/phish", "/fallback/") == "/fallback/"


def test_safe_next_url_allows_local_targets_only_for_current_scheme():
    request = RequestFactory().post("/action/", secure=True, HTTP_HOST="testserver")

    assert safe_next_url(request, "/dashboard/?page=2", "/fallback/") == "/dashboard/?page=2"
    assert safe_next_url(request, "https://testserver/dashboard/", "/fallback/") == "https://testserver/dashboard/"
    assert safe_next_url(request, "http://testserver/dashboard/", "/fallback/") == "/fallback/"


@pytest.mark.django_db
def test_state_action_rejects_external_next_redirect(client, django_user_model):
    permission = PermissionCode.objects.create(
        module="accounts",
        code="accounts.manage_users",
        name="Manage users",
    )
    role = Role.objects.create(code="redirect-security", name="Redirect security")
    role.permissions.add(permission)
    actor = django_user_model.objects.create_user(
        username="redirect-admin",
        email="redirect-admin@example.com",
        password="test12345",
    )
    target = django_user_model.objects.create_user(
        username="redirect-target",
        email="redirect-target@example.com",
        password="test12345",
    )
    UserRole.objects.create(user=actor, role=role)
    client.force_login(actor)

    response = client.post(
        reverse("accounts:user_toggle_active", kwargs={"pk": target.pk}),
        {"next": "https://evil.example/phish"},
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("accounts:user_detail", kwargs={"pk": target.pk})
