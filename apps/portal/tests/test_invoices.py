"""ES: Este módulo especifica regresiones ejecutables para el dominio de portal cliente.

EN: This module specifies executable regressions for the portal domain.

Contexto existente / Existing context:
Regression coverage for invoices in the portal domain.
"""

from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import close_old_connections, connection
from django.urls import reverse

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.audit.models import AuditLog
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.documents.models import PrivateDocument
from apps.invoices.models import InvoiceLine, InvoiceRecord
from apps.invoices.services import ensure_invoice_pdf, issue_invoice, recalculate_invoice_totals, void_invoice
from apps.notifications.models import NotificationMessage
from apps.portal.selectors import portal_invoices_queryset


@pytest.fixture
def invoice_portal_context(db, django_user_model):
    portal_permission, _ = PermissionCode.objects.update_or_create(
        code="portal.access", defaults={"module": "portal", "name": "Acceso al portal"}
    )
    view_permission, _ = PermissionCode.objects.update_or_create(
        code="invoices.view", defaults={"module": "invoices", "name": "Ver facturas"}
    )
    issue_permission, _ = PermissionCode.objects.update_or_create(
        code="invoices.issue", defaults={"module": "invoices", "name": "Emitir facturas"}
    )
    void_permission, _ = PermissionCode.objects.update_or_create(
        code="invoices.void", defaults={"module": "invoices", "name": "Anular facturas"}
    )
    client_role, _ = Role.objects.update_or_create(
        code="cliente", defaults={"name": "Cliente", "level": 100, "is_active": True}
    )
    client_role.permissions.add(portal_permission)
    staff_role = Role.objects.create(code="billing-portal-test", name="Facturación portal")
    staff_role.permissions.add(view_permission, issue_permission, void_permission)
    company = Company.objects.create(
        legal_name="Facturas Portal S.A.", commercial_name="Facturas Portal", ruc="1790000000051"
    )
    branch = Branch.objects.create(company=company, name="Matriz facturas", code="FAC-POR")
    user = django_user_model.objects.create_user(
        username="invoice-client", email="invoice-client@example.com", password="x"
    )
    other_user = django_user_model.objects.create_user(
        username="invoice-other", email="invoice-other@example.com", password="x"
    )
    staff = django_user_model.objects.create_user(
        username="invoice-staff", email="invoice-staff@example.com", password="x"
    )
    UserRole.objects.create(user=user, role=client_role)
    UserRole.objects.create(user=other_user, role=client_role)
    UserRole.objects.create(user=staff, role=staff_role)
    customer = Customer.objects.create(
        first_name="Cliente",
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
    return user, customer, other_user, other_customer, staff, company, branch


def _invoice(*, number, customer, company, branch, status=InvoiceRecord.Status.DRAFT):
    invoice = InvoiceRecord.objects.create(
        number=number,
        status=status,
        company=company,
        branch=branch,
        customer=customer,
        customer_name=customer.display_name,
        customer_email=customer.email,
    )
    line = InvoiceLine.objects.create(
        invoice=invoice,
        description="Servicio VINOVA",
        quantity=Decimal("1.00"),
        unit_price=Decimal("100.00"),
        tax_rate=Decimal("15.00"),
    )
    line.calculate_totals()
    line.save()
    recalculate_invoice_totals(invoice)
    invoice.refresh_from_db()
    return invoice


@pytest.mark.django_db
def test_issuing_invoice_creates_one_reproducible_private_pdf(
    invoice_portal_context,
    django_capture_on_commit_callbacks,
):
    _, customer, _, _, staff, company, branch = invoice_portal_context
    invoice = _invoice(number="FAC-PORTAL-0001", customer=customer, company=company, branch=branch)

    with django_capture_on_commit_callbacks(execute=True):
        issue_invoice(actor=staff, invoice=invoice)
    invoice.refresh_from_db()
    first = invoice.linked_document
    with first.file.open("rb") as handle:
        first_payload = handle.read()
    second = ensure_invoice_pdf(actor=staff, invoice=invoice)
    with second.file.open("rb") as handle:
        second_payload = handle.read()

    assert first.pk == second.pk
    assert first_payload == second_payload
    assert first_payload.startswith(b"%PDF-1.4")
    assert first.file_hash
    assert first.document_type == PrivateDocument.DocumentType.INVOICE
    assert first.customer_id == customer.pk
    assert PrivateDocument.objects.filter(linked_invoices=invoice).count() == 1
    notification = NotificationMessage.objects.get(dedup_key=f"invoice:{invoice.pk}:issued")
    assert notification.related_document_id == first.pk
    assert notification.recipients.get().customer_id == customer.pk


@pytest.mark.django_db
def test_voiding_invoice_notifies_customer_after_commit(
    invoice_portal_context,
    django_capture_on_commit_callbacks,
):
    _, customer, _, _, staff, company, branch = invoice_portal_context
    invoice = _invoice(number="FAC-PORTAL-VOID", customer=customer, company=company, branch=branch)
    with django_capture_on_commit_callbacks(execute=True):
        issue_invoice(actor=staff, invoice=invoice)
    with django_capture_on_commit_callbacks(execute=True):
        void_invoice(actor=staff, invoice=invoice, reason="Corrección solicitada")

    notification = NotificationMessage.objects.get(dedup_key=f"invoice:{invoice.pk}:void")
    assert notification.related_document_id == invoice.linked_document_id
    assert notification.recipients.get().customer_id == customer.pk


@pytest.mark.django_db
def test_portal_lists_only_own_non_draft_invoices(client, invoice_portal_context):
    user, customer, _, other_customer, staff, company, branch = invoice_portal_context
    own = _invoice(number="FAC-PORTAL-OWN", customer=customer, company=company, branch=branch)
    issue_invoice(actor=staff, invoice=own)
    draft = _invoice(number="FAC-PORTAL-DRAFT", customer=customer, company=company, branch=branch)
    foreign = _invoice(number="FAC-PORTAL-FOREIGN", customer=other_customer, company=company, branch=branch)
    issue_invoice(actor=staff, invoice=foreign)

    assert list(portal_invoices_queryset(customer).values_list("pk", flat=True)) == [own.pk]
    client.force_login(user)
    response = client.get(reverse("portal:invoice_list"))
    content = response.content.decode()
    assert response.status_code == 200
    assert own.number in content
    assert draft.number not in content
    assert foreign.number not in content
    assert client.get(reverse("portal:invoice_detail", kwargs={"pk": foreign.pk})).status_code == 404
    filtered = client.get(
        reverse("portal:invoice_list"),
        {"q": "OWN", "status": InvoiceRecord.Status.ISSUED},
    ).content.decode()
    assert own.number in filtered
    assert foreign.number not in filtered


@pytest.mark.django_db
def test_client_and_staff_download_same_private_artifact_with_audit(client, invoice_portal_context):
    user, customer, _, _, staff, company, branch = invoice_portal_context
    invoice = _invoice(number="FAC-PORTAL-DOWNLOAD", customer=customer, company=company, branch=branch)
    issue_invoice(actor=staff, invoice=invoice)
    invoice.refresh_from_db()
    document_id = invoice.linked_document_id

    client.force_login(user)
    portal_response = client.get(reverse("portal:invoice_download", kwargs={"pk": invoice.pk}))
    portal_payload = b"".join(portal_response.streaming_content)
    assert portal_response.status_code == 200
    assert portal_response["Content-Type"] == "application/pdf"
    assert portal_response["Cache-Control"] == "private, no-store"
    assert portal_response["X-Content-Type-Options"] == "nosniff"

    client.force_login(staff)
    staff_response = client.get(reverse("invoices_internal:pdf_download", kwargs={"pk": invoice.pk}))
    staff_payload = b"".join(staff_response.streaming_content)
    assert staff_response.status_code == 200
    assert staff_payload == portal_payload
    invoice.refresh_from_db()
    assert invoice.linked_document_id == document_id
    assert AuditLog.objects.filter(action="documents.private.download", object_id=str(document_id)).count() == 2


@pytest.mark.django_db
def test_missing_invoice_pdf_returns_404_without_false_download_audit(client, invoice_portal_context):
    user, customer, _, _, staff, company, branch = invoice_portal_context
    invoice = _invoice(number="FAC-PORTAL-MISSING", customer=customer, company=company, branch=branch)
    issue_invoice(actor=staff, invoice=invoice)
    invoice.refresh_from_db()
    document = invoice.linked_document
    document.file.storage.delete(document.file.name)

    client.force_login(user)
    assert client.get(reverse("portal:invoice_download", kwargs={"pk": invoice.pk})).status_code == 404
    client.force_login(staff)
    assert client.get(reverse("invoices_internal:pdf_download", kwargs={"pk": invoice.pk})).status_code == 404
    assert not AuditLog.objects.filter(
        action="documents.private.download",
        object_id=str(document.pk),
    ).exists()


@pytest.mark.django_db
def test_invoice_pdf_failure_rolls_back_database_and_storage(
    invoice_portal_context,
    settings,
    tmp_path,
    monkeypatch,
):
    _, customer, _, _, staff, company, branch = invoice_portal_context
    settings.PRIVATE_STORAGE_ROOT = tmp_path / "private-invoice-failure"
    invoice = _invoice(
        number="FAC-PORTAL-ROLLBACK",
        customer=customer,
        company=company,
        branch=branch,
        status=InvoiceRecord.Status.ISSUED,
    )

    def fail_audit(**kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("apps.invoices.services.audit_log", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        ensure_invoice_pdf(actor=staff, invoice=invoice)

    invoice.refresh_from_db()
    assert invoice.linked_document_id is None
    assert not PrivateDocument.objects.filter(title__contains=invoice.number).exists()
    assert not [path for path in settings.PRIVATE_STORAGE_ROOT.rglob("*") if path.is_file()]


@pytest.mark.django_db
def test_invoice_never_moves_to_another_customer(client, invoice_portal_context):
    user, customer, other_user, other_customer, staff, company, branch = invoice_portal_context
    invoice = _invoice(number="FAC-PORTAL-PERSONAL", customer=customer, company=company, branch=branch)
    issue_invoice(actor=staff, invoice=invoice)

    client.force_login(other_user)
    assert client.get(reverse("portal:invoice_detail", kwargs={"pk": invoice.pk})).status_code == 404
    assert not portal_invoices_queryset(other_customer).filter(pk=invoice.pk).exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_pdf_generation_keeps_single_artifact(invoice_portal_context, django_user_model):
    if connection.vendor != "postgresql":
        pytest.skip("La prueba de bloqueo concurrente requiere PostgreSQL.")
    _, customer, _, _, staff, company, branch = invoice_portal_context
    invoice = _invoice(
        number="FAC-PORTAL-RACE",
        customer=customer,
        company=company,
        branch=branch,
        status=InvoiceRecord.Status.ISSUED,
    )
    barrier = Barrier(2)

    def generate():
        close_old_connections()
        try:
            actor = django_user_model.objects.get(pk=staff.pk)
            current = InvoiceRecord.objects.get(pk=invoice.pk)
            barrier.wait(timeout=10)
            return ensure_invoice_pdf(actor=actor, invoice=current).pk
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        document_ids = list(pool.map(lambda _: generate(), range(2)))

    invoice.refresh_from_db()
    assert len(set(document_ids)) == 1
    assert document_ids[0] == invoice.linked_document_id
    assert PrivateDocument.objects.filter(linked_invoices=invoice).count() == 1
