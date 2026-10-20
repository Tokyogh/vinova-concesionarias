"""ES: Este módulo especifica regresiones ejecutables para el dominio de API e integraciones.

EN: This module specifies executable regressions for the api domain.

Contexto existente / Existing context:
Regression coverage for integration scope v170 in the api domain.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.api.forms import APIClientForm
from apps.api.models import APIScope, IntegrationLog
from apps.api.selectors import integration_branch_ids
from apps.api.services import log_integration
from apps.branches.models import Branch
from apps.companies.models import Company


pytestmark = pytest.mark.django_db


def test_integration_scope_ignores_expired_and_future_roles(django_user_model):
    company = Company.objects.create(legal_name="Integration Scope SA", commercial_name="Integration Scope", ruc="1799999999010")
    branch = Branch.objects.create(company=company, name="Principal", code="INT-SCOPE", city="Quito")
    permission = PermissionCode.objects.create(module="integrations", code="integrations.view", name="View integrations")
    role = Role.objects.create(code="integration-temporal", name="Integration temporal")
    role.permissions.add(permission)
    expired = django_user_model.objects.create_user(
        username="integration-expired",
        email="integration-expired@example.com",
        password="test12345",
    )
    future = django_user_model.objects.create_user(
        username="integration-future",
        email="integration-future@example.com",
        password="test12345",
    )
    UserRole.objects.create(user=expired, role=role, branch=branch, expires_at=timezone.now() - timedelta(seconds=1))
    UserRole.objects.create(user=future, role=role, branch=branch, starts_at=timezone.now() + timedelta(days=1))

    assert integration_branch_ids(expired) == set()
    assert integration_branch_ids(future) == set()


def test_branch_api_client_form_requires_service_user_role_in_branch(django_user_model):
    company = Company.objects.create(legal_name="Service User Scope SA", commercial_name="Service User Scope", ruc="1799999999011")
    branch = Branch.objects.create(company=company, name="Principal", code="SERVICE-SCOPE", city="Quito")
    permission = PermissionCode.objects.create(module="integrations", code="integrations.manage", name="Manage integrations")
    manager_role = Role.objects.create(code="integration-manager-scope", name="Integration manager")
    manager_role.permissions.add(permission)
    service_role = Role.objects.create(code="integration-service-scope", name="Integration service")
    manager = django_user_model.objects.create_user(
        username="integration-manager-scope",
        email="integration-manager-scope@example.com",
        password="test12345",
    )
    service_user = django_user_model.objects.create_user(
        username="integration-service-scope",
        email="integration-service-scope@example.com",
        password="test12345",
        branch=branch,
    )
    UserRole.objects.create(user=manager, role=manager_role, branch=branch)
    scope = APIScope.objects.create(code="api:read", name="API read")
    payload = {
        "name": "Scoped client",
        "service_user": service_user.pk,
        "branch": branch.pk,
        "scopes": [scope.pk],
        "rate_limit": "60/hour",
    }

    form = APIClientForm(payload, user=manager)
    assert form.is_valid() is False
    assert "service_user" in form.errors

    UserRole.objects.create(user=service_user, role=service_role, branch=branch)
    form = APIClientForm(payload, user=manager)
    assert form.is_valid() is True


def test_integration_errors_are_redacted_before_database_storage():
    event = log_integration(
        direction=IntegrationLog.Direction.OUTBOUND,
        category="webhook",
        action="security-test",
        status=IntegrationLog.Status.FAILED,
        error_message='Authorization: Bearer bearer-value {"token": "token-value"}',
    )

    assert "bearer-value" not in event.error_message
    assert "token-value" not in event.error_message
