"""ES: Este módulo especifica regresiones ejecutables para el dominio de cuentas.

EN: This module specifies executable regressions for the accounts domain.

Contexto existente / Existing context:
Regression coverage for qa client preparation in the accounts domain.
"""

from __future__ import annotations

import pytest
from django.core.management import CommandError, call_command

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.accounts.qa_safety import assert_non_production_database
from apps.audit.models import AuditLog
from apps.customers.models import Customer


@pytest.fixture
def qa_preparation_context(db, django_user_model):
    portal_permission, _ = PermissionCode.objects.update_or_create(
        code="portal.access", defaults={"module": "portal", "name": "Acceso al portal"}
    )
    manage_permission, _ = PermissionCode.objects.update_or_create(
        code="customers.manage",
        defaults={"module": "customers", "name": "Gestionar clientes"},
    )
    client_role, _ = Role.objects.update_or_create(
        code="cliente", defaults={"name": "Cliente", "level": 100, "is_active": True}
    )
    client_role.permissions.add(portal_permission)
    manager_role, _ = Role.objects.update_or_create(
        code="qa_manager", defaults={"name": "QA Manager", "level": 10, "is_active": True}
    )
    manager_role.permissions.add(manage_permission)

    actor = django_user_model.objects.create_user(
        username="qa-operator", email="qa-operator@example.invalid", password="operator-password"
    )
    UserRole.objects.create(user=actor, role=manager_role)
    user = django_user_model.objects.create_user(
        username="legacy-qa-client",
        email="legacy-qa-client@example.invalid",
        password="password-must-not-change",
        first_name="QA",
        last_name="Anterior",
    )
    UserRole.objects.create(user=user, role=client_role)
    return actor, user


@pytest.mark.django_db
def test_prepare_qa_client_account_is_audited_idempotent_and_preserves_password(
    qa_preparation_context, monkeypatch
):
    actor, user = qa_preparation_context
    monkeypatch.setenv("VINOVA_ENVIRONMENT", "test")
    password_hash = user.password

    call_command(
        "prepare_qa_client_account",
        user_id=user.pk,
        actor_id=actor.pk,
        apply=True,
        verbosity=0,
    )

    customer = Customer.objects.get(account=user)
    user.refresh_from_db()
    assert customer.status == Customer.Status.ACTIVE
    assert not customer.is_deleted
    assert customer.source == "qa_portal_compatibility"
    assert user.password == password_hash
    assert AuditLog.objects.filter(action="customers.create", object_id=str(customer.pk)).exists()
    assert AuditLog.objects.filter(action="customers.account_link", object_id=str(customer.pk)).exists()

    customer_count = Customer.objects.count()
    audit_count = AuditLog.objects.count()
    call_command(
        "prepare_qa_client_account",
        user_id=user.pk,
        actor_id=actor.pk,
        apply=True,
        verbosity=0,
    )

    assert Customer.objects.count() == customer_count
    assert AuditLog.objects.count() == audit_count
    user.refresh_from_db()
    assert user.password == password_hash


@pytest.mark.django_db
def test_prepare_qa_client_account_refuses_ambiguous_existing_customer(
    qa_preparation_context, monkeypatch
):
    actor, user = qa_preparation_context
    monkeypatch.setenv("VINOVA_ENVIRONMENT", "test")
    candidate = Customer.objects.create(
        first_name="Expediente",
        email=user.email,
        status=Customer.Status.ACTIVE,
    )

    with pytest.raises(CommandError, match="ambigua"):
        call_command(
            "prepare_qa_client_account",
            user_id=user.pk,
            actor_id=actor.pk,
            apply=True,
            verbosity=0,
        )

    candidate.refresh_from_db()
    assert candidate.account_id is None
    assert Customer.objects.count() == 1


@pytest.mark.django_db
def test_prepare_qa_client_account_refuses_staff_target(qa_preparation_context, monkeypatch):
    actor, user = qa_preparation_context
    monkeypatch.setenv("VINOVA_ENVIRONMENT", "test")
    user.is_staff = True
    user.save(update_fields=["is_staff"])

    with pytest.raises(CommandError, match="Staff"):
        call_command(
            "prepare_qa_client_account",
            user_id=user.pk,
            actor_id=actor.pk,
            apply=True,
            verbosity=0,
        )

    assert not Customer.objects.filter(account=user).exists()


@pytest.mark.django_db
def test_prepare_qa_client_account_does_not_reactivate_existing_profile(
    qa_preparation_context, monkeypatch
):
    actor, user = qa_preparation_context
    monkeypatch.setenv("VINOVA_ENVIRONMENT", "test")
    customer = Customer.objects.create(
        first_name="QA",
        email=user.email,
        account=user,
        status=Customer.Status.INACTIVE,
    )

    with pytest.raises(CommandError, match="flujo empresarial"):
        call_command(
            "prepare_qa_client_account",
            user_id=user.pk,
            actor_id=actor.pk,
            apply=True,
            verbosity=0,
        )

    customer.refresh_from_db()
    assert customer.status == Customer.Status.INACTIVE


@pytest.mark.django_db
def test_prepare_qa_client_account_is_blocked_in_production(qa_preparation_context, monkeypatch):
    actor, user = qa_preparation_context
    monkeypatch.setenv("VINOVA_ENVIRONMENT", "production")

    with pytest.raises(CommandError, match="prohibido en producción"):
        call_command(
            "prepare_qa_client_account",
            user_id=user.pk,
            actor_id=actor.pk,
            apply=True,
            verbosity=0,
        )

    assert not Customer.objects.filter(account=user).exists()


def test_qa_safety_accepts_dedicated_compose_host_only_in_test_environment(settings, monkeypatch):
    """ES: Reconoce la base efímera del stack QA sin ampliar hosts remotos.

    EN: Recognizes the ephemeral QA-stack database without broadening remote hosts.
    """

    monkeypatch.setenv("VINOVA_ENVIRONMENT", "test")
    settings.DATABASES["default"]["HOST"] = "qa_db"
    assert_non_production_database()


def test_qa_safety_still_rejects_remote_host_in_test_environment(settings, monkeypatch):
    monkeypatch.setenv("VINOVA_ENVIRONMENT", "test")
    settings.DATABASES["default"]["HOST"] = "database.example.invalid"
    with pytest.raises(CommandError, match="no parece local"):
        assert_non_production_database()
