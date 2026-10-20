"""ES: Este módulo especifica regresiones ejecutables para el dominio de portal cliente.

EN: This module specifies executable regressions for the portal domain.

Contexto existente / Existing context:
Regression coverage for notifications in the portal domain.
"""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import FileSystemStorage
from django.db import close_old_connections, connection, connections
from django.urls import reverse

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.documents.forms import PrivateDocumentForm
from apps.documents.models import PrivateDocument
from apps.documents.services import create_private_document
from apps.notifications.models import (
    CustomerNotificationPreference,
    NotificationMessage,
    NotificationRecipient,
)
from apps.notifications.services import create_customer_event_notification


@pytest.fixture
def notification_portal_context(db, django_user_model):
    permission, _ = PermissionCode.objects.update_or_create(
        code="portal.access",
        defaults={"module": "portal", "name": "Acceso al portal"},
    )
    role, _ = Role.objects.update_or_create(
        code="cliente",
        defaults={"name": "Cliente", "level": 100, "is_active": True},
    )
    role.permissions.add(permission)
    company = Company.objects.create(
        legal_name="Notificaciones Portal S.A.",
        commercial_name="Notificaciones Portal",
        ruc="1790000000043",
    )
    branch = Branch.objects.create(company=company, name="Matriz avisos", code="NOT-POR")
    user = django_user_model.objects.create_user(
        username="notification-client",
        email="notification-client@example.com",
        password="x",
    )
    other_user = django_user_model.objects.create_user(
        username="notification-other",
        email="notification-other@example.com",
        password="x",
    )
    UserRole.objects.create(user=user, role=role)
    UserRole.objects.create(user=other_user, role=role)
    customer = Customer.objects.create(
        first_name="Cliente",
        last_name="Avisos",
        email=user.email,
        account=user,
        assigned_branch=branch,
        status=Customer.Status.ACTIVE,
    )
    other_customer = Customer.objects.create(
        first_name="Otro",
        email=other_user.email,
        account=other_user,
        assigned_branch=branch,
        status=Customer.Status.ACTIVE,
    )
    return user, customer, other_user, other_customer, branch


def _recipient(*, customer, title, dedup_key):
    message = NotificationMessage.objects.create(
        title=title,
        body=f"Contenido privado de {title}",
        message_type=NotificationMessage.MessageType.ALERT,
        related_customer=customer,
        dedup_key=dedup_key,
    )
    return NotificationRecipient.objects.create(
        notification=message,
        recipient_type=NotificationRecipient.RecipientType.CUSTOMER,
        customer=customer,
        display_name_snapshot=customer.display_name,
        email_snapshot=customer.email,
    )


@pytest.mark.django_db
def test_portal_inbox_isolates_customer_recipients_and_marks_read(client, notification_portal_context):
    user, customer, _, other_customer, _ = notification_portal_context
    own = _recipient(customer=customer, title="Aviso propio", dedup_key="portal-own")
    foreign = _recipient(customer=other_customer, title="Aviso ajeno", dedup_key="portal-foreign")
    staff_message = NotificationMessage.objects.create(
        title="Aviso interno",
        body="No debe aparecer en el portal",
        dedup_key="portal-user-recipient",
    )
    NotificationRecipient.objects.create(
        notification=staff_message,
        recipient_type=NotificationRecipient.RecipientType.USER,
        user=user,
        display_name_snapshot=user.username,
        email_snapshot=user.email,
    )
    client.force_login(user)

    response = client.get(reverse("portal:notification_list"))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Aviso propio" in content
    assert "Aviso ajeno" not in content
    assert "Aviso interno" in content
    assert client.get(reverse("portal:notification_detail", kwargs={"pk": foreign.pk})).status_code == 404
    filtered = client.get(
        reverse("portal:notification_list"),
        {
            "q": "propio",
            "message_type": NotificationMessage.MessageType.ALERT,
            "delivery_status": NotificationRecipient.DeliveryStatus.UNREAD,
        },
    ).content.decode()
    assert "Aviso propio" in filtered
    assert "Aviso interno" not in filtered
    detail = client.get(reverse("portal:notification_detail", kwargs={"pk": own.pk}))
    assert detail.status_code == 200
    own.refresh_from_db()
    assert own.status == NotificationRecipient.DeliveryStatus.READ
    assert own.read_at is not None


@pytest.mark.django_db
def test_portal_archives_only_own_notification(client, notification_portal_context):
    user, customer, _, other_customer, _ = notification_portal_context
    own = _recipient(customer=customer, title="Archivable", dedup_key="portal-archive-own")
    foreign = _recipient(customer=other_customer, title="No archivable", dedup_key="portal-archive-foreign")
    client.force_login(user)

    response = client.post(reverse("portal:notification_archive", kwargs={"pk": own.pk}))

    assert response.status_code == 302
    own.refresh_from_db()
    assert own.status == NotificationRecipient.DeliveryStatus.ARCHIVED
    assert "Archivable" not in client.get(reverse("portal:notification_list")).content.decode()
    assert client.post(reverse("portal:notification_archive", kwargs={"pk": foreign.pk})).status_code == 404


@pytest.mark.django_db
def test_portal_marks_all_customer_and_user_recipients_read(client, notification_portal_context):
    user, customer, _, other_customer, _ = notification_portal_context
    own_customer = _recipient(customer=customer, title="Cliente", dedup_key="read-all-customer")
    foreign = _recipient(customer=other_customer, title="Ajeno", dedup_key="read-all-foreign")
    own_user_message = NotificationMessage.objects.create(
        title="Cuenta",
        body="Aviso directo a la cuenta",
        dedup_key="read-all-user",
    )
    own_user = NotificationRecipient.objects.create(
        notification=own_user_message,
        recipient_type=NotificationRecipient.RecipientType.USER,
        user=user,
    )
    client.force_login(user)

    response = client.post(reverse("portal:notification_read_all"))

    assert response.status_code == 302
    own_customer.refresh_from_db()
    own_user.refresh_from_db()
    foreign.refresh_from_db()
    assert own_customer.status == NotificationRecipient.DeliveryStatus.READ
    assert own_user.status == NotificationRecipient.DeliveryStatus.READ
    assert foreign.status == NotificationRecipient.DeliveryStatus.UNREAD


@pytest.mark.django_db
def test_customer_event_is_idempotent_and_respects_preferences(notification_portal_context):
    _, customer, _, _, branch = notification_portal_context

    first = create_customer_event_notification(
        customer=customer,
        title="Factura lista",
        body="Tu comprobante está disponible.",
        message_type=NotificationMessage.MessageType.INVOICE,
        dedup_key="invoice:77:issued",
        branch=branch,
    )
    second = create_customer_event_notification(
        customer=customer,
        title="Factura repetida",
        body="No debe duplicarse.",
        message_type=NotificationMessage.MessageType.INVOICE,
        dedup_key="invoice:77:issued",
        branch=branch,
    )

    assert first.pk == second.pk
    assert NotificationMessage.objects.filter(dedup_key="invoice:77:issued").count() == 1
    assert first.recipients.filter(customer=customer).count() == 1

    preference = customer.notification_preference
    preference.document_updates = False
    preference.save(update_fields=["document_updates", "updated_at"])
    blocked = create_customer_event_notification(
        customer=customer,
        title="Documento bloqueado",
        body="No debe crearse.",
        message_type=NotificationMessage.MessageType.DOCUMENT,
        dedup_key="document:88:published",
        branch=branch,
    )
    assert blocked is None
    assert not NotificationMessage.objects.filter(dedup_key="document:88:published").exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_customer_event_keeps_one_message_and_recipient(notification_portal_context):
    if connection.vendor != "postgresql":
        pytest.skip("La prueba de idempotencia concurrente requiere PostgreSQL.")
    _, customer, _, _, _ = notification_portal_context
    barrier = Barrier(2)

    def publish():
        close_old_connections()
        try:
            current_customer = Customer.objects.get(pk=customer.pk)
            barrier.wait(timeout=10)
            return create_customer_event_notification(
                customer=current_customer,
                title="Evento concurrente",
                body="Debe existir una sola vez.",
                message_type=NotificationMessage.MessageType.ALERT,
                dedup_key="customer-event:concurrent",
            ).pk
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        message_ids = list(pool.map(lambda _: publish(), range(2)))

    assert len(set(message_ids)) == 1
    message = NotificationMessage.objects.get(dedup_key="customer-event:concurrent")
    assert message.recipients.filter(customer=customer).count() == 1


@pytest.mark.django_db
def test_portal_updates_notification_preferences(client, notification_portal_context):
    user, customer, _, _, _ = notification_portal_context
    client.force_login(user)

    response = client.post(
        reverse("portal:settings"),
        {
            "invoice_updates": "on",
            "service_updates": "on",
            "email_enabled": "on",
        },
    )

    assert response.status_code == 302
    preference = CustomerNotificationPreference.objects.get(customer=customer)
    assert preference.invoice_updates is True
    assert preference.document_updates is False
    assert preference.service_updates is True
    assert preference.general_alerts is False
    assert preference.email_enabled is True


@pytest.mark.django_db
def test_private_document_publication_creates_one_customer_event(
    notification_portal_context,
    django_user_model,
    monkeypatch,
    tmp_path,
    django_capture_on_commit_callbacks,
):
    _, customer, _, _, branch = notification_portal_context
    actor = django_user_model.objects.create_superuser(
        username="notification-doc-admin",
        email="notification-doc-admin@example.com",
        password="x",
    )
    monkeypatch.setattr(
        PrivateDocument._meta.get_field("file"),
        "storage",
        FileSystemStorage(location=tmp_path),
    )
    form = PrivateDocumentForm(
        data={
            "title": "Contrato publicado",
            "document_type": PrivateDocument.DocumentType.CONTRACT,
            "status": PrivateDocument.Status.ACTIVE,
            "branch": branch.pk,
            "customer": customer.pk,
            "is_confidential": True,
        },
        files={
            "file": SimpleUploadedFile(
                "contrato-publicado.pdf",
                b"%PDF-1.4 notification test",
                content_type="application/pdf",
            )
        },
        user=actor,
    )
    assert form.is_valid(), form.errors

    with django_capture_on_commit_callbacks(execute=True):
        document = create_private_document(actor=actor, form=form)

    message = NotificationMessage.objects.get(dedup_key=f"document:{document.pk}:published")
    assert message.related_document_id == document.pk
    assert message.recipients.get().customer_id == customer.pk
