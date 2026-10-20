"""ES: Este módulo especifica regresiones ejecutables para el dominio de notificaciones.

EN: This module specifies executable regressions for the notifications domain.

Contexto existente / Existing context:
Regression coverage for notification scope v160 in the notifications domain.
"""

from __future__ import annotations

import pytest

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.notifications.forms import NotificationMessageForm
from apps.notifications.models import NotificationMessage, NotificationRecipient
from apps.notifications.services import create_notification_message


@pytest.fixture
def scoped_data(django_user_model):
    company = Company.objects.create(legal_name="Scope SA", commercial_name="Scope", ruc="1799999999001")
    branch_a = Branch.objects.create(
        company=company, name="Norte", code="NOT-A", branch_type=Branch.BranchType.DEALERSHIP, city="Quito"
    )
    branch_b = Branch.objects.create(
        company=company, name="Sur", code="NOT-B", branch_type=Branch.BranchType.DEALERSHIP, city="Quito"
    )
    permissions = []
    for code in ("dashboard.view", "notifications.view", "notifications.send"):
        permissions.append(PermissionCode.objects.create(module=code.split(".")[0], code=code, name=code))
    role = Role.objects.create(code="branch_notifier", name="Branch notifier")
    role.permissions.add(*permissions)
    sender = django_user_model.objects.create_user(username="sender-a", email="sender-a@example.com", password="x")
    recipient_a = django_user_model.objects.create_user(
        username="recipient-a", email="recipient-a@example.com", password="x"
    )
    recipient_b = django_user_model.objects.create_user(
        username="recipient-b", email="recipient-b@example.com", password="x"
    )
    UserRole.objects.create(user=sender, role=role, branch=branch_a)
    UserRole.objects.create(user=recipient_a, role=role, branch=branch_a)
    UserRole.objects.create(user=recipient_b, role=role, branch=branch_b)
    customer_a = Customer.objects.create(first_name="Ana", identification_number="1000000001", assigned_branch=branch_a)
    customer_b = Customer.objects.create(
        first_name="Berta", identification_number="1000000002", assigned_branch=branch_b
    )
    return sender, recipient_a, recipient_b, branch_a, branch_b, customer_a, customer_b


@pytest.mark.django_db
def test_compose_and_lookups_are_branch_scoped(client, scoped_data):
    sender, recipient_a, recipient_b, branch_a, branch_b, customer_a, customer_b = scoped_data
    form = NotificationMessageForm(user=sender)
    assert list(form.fields["branch"].queryset) == [branch_a]
    assert list(form.fields["recipient_users"].queryset) == [recipient_a, sender]
    assert list(form.fields["recipient_customers"].queryset) == [customer_a]

    client.force_login(sender)
    response = client.get("/dashboard/lookups/customers/?q=")
    ids = {item["id"] for item in response.json()["results"]}
    assert customer_a.pk in ids
    assert customer_b.pk not in ids
    response = client.get("/dashboard/lookups/users/?q=")
    ids = {item["id"] for item in response.json()["results"]}
    assert recipient_a.pk in ids
    assert recipient_b.pk not in ids


@pytest.mark.django_db
def test_branch_sender_cannot_submit_cross_branch_recipient(scoped_data):
    sender, recipient_a, recipient_b, branch_a, branch_b, customer_a, customer_b = scoped_data
    form = NotificationMessageForm(
        data={
            "title": "Fuera de alcance",
            "body": "No debe enviarse",
            "message_type": NotificationMessage.MessageType.ALERT,
            "priority": NotificationMessage.Priority.NORMAL,
            "branch": branch_b.pk,
            "recipient_users": [recipient_b.pk],
            "recipient_customers": [customer_b.pk],
        },
        user=sender,
    )
    assert not form.is_valid()
    assert NotificationMessage.objects.count() == 0


@pytest.mark.django_db
def test_notification_dedup_key_is_idempotent(scoped_data):
    sender, recipient_a, recipient_b, branch_a, branch_b, customer_a, customer_b = scoped_data
    data = {
        "title": "Reserva por vencer",
        "body": "Revisar reserva",
        "message_type": NotificationMessage.MessageType.SYSTEM,
        "priority": NotificationMessage.Priority.HIGH,
        "branch": branch_a.pk,
        "recipient_users": [recipient_a.pk],
        "recipient_customers": [],
    }
    first_form = NotificationMessageForm(data=data, user=sender)
    second_form = NotificationMessageForm(data=data, user=sender)
    assert first_form.is_valid(), first_form.errors
    assert second_form.is_valid(), second_form.errors
    first = create_notification_message(actor=sender, form=first_form, dedup_key="reservation-expiry:42")
    second = create_notification_message(actor=sender, form=second_form, dedup_key="reservation-expiry:42")
    assert first.pk == second.pk
    assert NotificationMessage.objects.count() == 1
    assert first.recipients.count() == 1


@pytest.mark.django_db
def test_cross_branch_recipient_can_read_but_cannot_manage_message(client, scoped_data):
    sender, recipient_a, recipient_b, branch_a, branch_b, customer_a, customer_b = scoped_data
    message = NotificationMessage.objects.create(
        title="Privado sucursal sur",
        body="Contenido",
        branch=branch_b,
        sender=recipient_b,
        created_by=recipient_b,
    )
    NotificationRecipient.objects.create(
        notification=message,
        recipient_type=NotificationRecipient.RecipientType.USER,
        user=sender,
        display_name_snapshot="Usuario Norte",
    )
    NotificationRecipient.objects.create(
        notification=message,
        recipient_type=NotificationRecipient.RecipientType.USER,
        user=recipient_b,
        display_name_snapshot="Destinatario secreto Sur",
    )
    client.force_login(sender)

    detail = client.get(f"/dashboard/notifications/{message.pk}/")
    assert detail.status_code == 200
    assert b"Destinatario secreto Sur" not in detail.content
    sent = client.get("/dashboard/notifications/sent/")
    assert message.title.encode() not in sent.content
    archive = client.post(f"/dashboard/notifications/{message.pk}/archive/")
    assert archive.status_code == 404
    message.refresh_from_db()
    assert not message.is_deleted
