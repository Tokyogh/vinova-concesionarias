"""ES: Este módulo especifica regresiones ejecutables para el dominio de notificaciones.

EN: This module specifies executable regressions for the notifications domain.

Contexto existente / Existing context:
Regression coverage for notifications search ux in the notifications domain.
"""

from __future__ import annotations

import pytest

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.notifications.forms import NotificationMessageForm
from apps.notifications.models import NotificationMessage, NotificationRecipient, NotificationTemplate
from apps.notifications.services import create_notification_message


@pytest.fixture
def notification_permissions():
    perms = {}
    for code in ["dashboard.view", "notifications.view", "notifications.send", "notifications.manage_templates", "customers.view"]:
        perms[code] = PermissionCode.objects.create(module=code.split(".")[0], code=code, name=code)
    return perms


@pytest.fixture
def notification_manager(django_user_model, notification_permissions):
    user = django_user_model.objects.create_user(username="notifyadmin", email="notifyadmin@example.com", password="x")
    role = Role.objects.create(code="notify_admin", name="Administrador de notificaciones")
    role.permissions.add(*notification_permissions.values())
    UserRole.objects.create(user=user, role=role)
    return user


@pytest.fixture
def notification_user(django_user_model, notification_permissions):
    user = django_user_model.objects.create_user(username="recipient", email="recipient@example.com", password="x")
    role = Role.objects.create(code="notify_viewer", name="Visualizador de notificaciones")
    role.permissions.add(notification_permissions["notifications.view"])
    UserRole.objects.create(user=user, role=role)
    return user


@pytest.fixture
def branch():
    company = Company.objects.create(legal_name="Mensajes Demo S.A.", commercial_name="Mensajes Demo", ruc="1790010010001")
    return Branch.objects.create(company=company, name="Sucursal Centro", code="MSG-001", branch_type=Branch.BranchType.DEALERSHIP, city="Quito")


@pytest.fixture
def customer(branch):
    return Customer.objects.create(first_name="María", last_name="López", email="maria@example.com", identification_number="0911111111", assigned_branch=branch)


@pytest.mark.django_db
def test_notification_module_requires_login(client):
    response = client.get("/dashboard/notifications/")
    assert response.status_code == 302
    assert "/accounts/login/" in response.headers["Location"]


@pytest.mark.django_db
def test_notification_manager_can_send_to_user_and_customer(notification_manager, notification_user, customer, branch):
    template = NotificationTemplate.objects.create(name="Demo", template_type="general", subject="Seguimiento", body="Mensaje base", created_by=notification_manager)
    form = NotificationMessageForm(
        data={
            "template": template.pk,
            "title": "Seguimiento comercial",
            "body": "Revisar avance del cliente.",
            "message_type": NotificationMessage.MessageType.MESSAGE,
            "priority": NotificationMessage.Priority.HIGH,
            "branch": branch.pk,
            "recipient_users": [notification_user.pk],
            "recipient_customers": [customer.pk],
        },
        user=notification_manager,
    )
    assert form.is_valid(), form.errors
    message = create_notification_message(actor=notification_manager, form=form)
    assert message.recipients.count() == 2
    assert message.priority == NotificationMessage.Priority.HIGH
    assert NotificationRecipient.objects.filter(notification=message, user=notification_user).exists()
    assert NotificationRecipient.objects.filter(notification=message, customer=customer).exists()


@pytest.mark.django_db
def test_inbox_marks_message_read_when_opened(client, notification_manager, notification_user, customer):
    form = NotificationMessageForm(
        data={
            "title": "Mensaje de lectura",
            "body": "Abrir para marcar leído.",
            "message_type": NotificationMessage.MessageType.ALERT,
            "priority": NotificationMessage.Priority.NORMAL,
            "recipient_users": [notification_user.pk],
            "recipient_customers": [],
        },
        user=notification_manager,
    )
    assert form.is_valid(), form.errors
    message = create_notification_message(actor=notification_manager, form=form)
    client.force_login(notification_user)
    response = client.get(f"/dashboard/notifications/{message.pk}/")
    assert response.status_code == 200
    recipient = NotificationRecipient.objects.get(notification=message, user=notification_user)
    assert recipient.status == NotificationRecipient.DeliveryStatus.READ
    assert recipient.read_at is not None


@pytest.mark.django_db
def test_internal_lookup_customers_returns_json(client, notification_manager, customer):
    client.force_login(notification_manager)
    response = client.get("/dashboard/lookups/customers/?q=María")
    assert response.status_code == 200
    payload = response.json()
    assert payload["results"]
    assert "María" in payload["results"][0]["text"]


@pytest.mark.django_db
def test_notification_compose_has_searchable_selects(client, notification_manager):
    client.force_login(notification_manager)
    response = client.get("/dashboard/notifications/compose/")
    assert response.status_code == 200
    assert b"data-searchable-select" in response.content
    assert b"Buscar clientes" in response.content or b"Buscar usuarios" in response.content
