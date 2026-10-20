"""ES: Este módulo especifica regresiones ejecutables para el dominio de facturación.

EN: This module specifies executable regressions for the invoices domain.

Contexto existente / Existing context:
Regression coverage for invoices billing in the invoices domain.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.invoices.models import InvoiceRecord, InvoiceSequence
from apps.invoices.services import (
    apply_payment,
    create_invoice_from_sale,
    issue_invoice,
    void_invoice,
)
from apps.sales.models import SaleLine, SalePayment, SaleRecord
from apps.sales.services import recalculate_sale_totals
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel


@pytest.fixture
def invoice_permissions():
    perms = {}
    for code in [
        "dashboard.view",
        "invoices.view",
        "invoices.issue",
        "invoices.manage",
        "invoices.void",
        "sales.sell",
        "documents.view",
    ]:
        perms[code] = PermissionCode.objects.create(module=code.split(".")[0], code=code, name=code)
    return perms


@pytest.fixture
def billing_user(django_user_model, invoice_permissions):
    user = django_user_model.objects.create_user(username="billing", email="billing@example.com", password="x")
    role = Role.objects.create(code="facturacion", name="Facturación")
    role.permissions.add(*invoice_permissions.values())
    UserRole.objects.create(user=user, role=role)
    return user


@pytest.fixture
def branch():
    company = Company.objects.create(
        legal_name="Automotores Demo S.A.", commercial_name="Automotores Demo", ruc="1790012300001"
    )
    return Branch.objects.create(
        company=company, name="Matriz Demo", code="MTR", branch_type=Branch.BranchType.DEALERSHIP, city="Quito"
    )


@pytest.fixture
def customer(branch):
    return Customer.objects.create(
        first_name="Daniela",
        last_name="Paz",
        identification_number="0911111111",
        email="daniela@example.com",
        phone="0990000000",
        assigned_branch=branch,
    )


@pytest.fixture
def vehicle(branch):
    brand = VehicleBrand.objects.create(name="Toyota")
    model = VehicleModel.objects.create(brand=brand, name="Hilux")
    return Vehicle.objects.create(
        brand=brand,
        model=model,
        branch=branch,
        year=2024,
        version="SRV",
        vin="VININV000001",
        public_slug="toyota-hilux-invoice",
        status=Vehicle.Status.SOLD,
        price="42000.00",
    )


@pytest.fixture
def sold_sale(branch, customer, vehicle, billing_user):
    sale = SaleRecord.objects.create(
        number="VEN-INV-0001",
        kind=SaleRecord.Kind.SALE,
        status=SaleRecord.Status.SOLD,
        customer=customer,
        branch=branch,
        advisor=billing_user,
        vehicle=vehicle,
        vehicle_price=Decimal("42000.00"),
        vehicle_discount=Decimal("1000.00"),
        tax_rate=Decimal("15.00"),
    )
    line = SaleLine.objects.create(
        sale=sale,
        description="Kit de entrega",
        quantity=Decimal("1.00"),
        unit_price=Decimal("250.00"),
        discount_amount=Decimal("0.00"),
    )
    line.calculate_totals()
    line.save()
    recalculate_sale_totals(sale)
    SalePayment.objects.create(
        sale=sale,
        method=SalePayment.Method.TRANSFER,
        status=SalePayment.Status.CONFIRMED,
        amount=Decimal("1000.00"),
        received_by=billing_user,
    )
    recalculate_sale_totals(sale)
    return sale


@pytest.mark.django_db
def test_invoice_module_requires_login(client):
    response = client.get("/dashboard/invoices/")
    assert response.status_code == 302
    assert "/accounts/login/" in response.headers["Location"]


@pytest.mark.django_db
def test_common_user_cannot_access_invoice_module(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="clientinvoice", email="clientinvoice@example.com", password="x"
    )
    client.force_login(user)
    response = client.get("/dashboard/invoices/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_create_invoice_from_sale_generates_number_and_lines(billing_user, sold_sale):
    invoice = create_invoice_from_sale(
        actor=billing_user,
        sale=sold_sale,
        invoice_type=InvoiceRecord.InvoiceType.INVOICE,
        issue_date=timezone.localdate(),
        due_date=timezone.localdate() + timedelta(days=15),
        notes="Entrega inmediata",
    )
    assert invoice.number.startswith("FAC-MTR-")
    assert invoice.status == InvoiceRecord.Status.DRAFT
    assert invoice.lines.count() == 2
    assert invoice.total == sold_sale.total
    assert InvoiceSequence.objects.get(branch=sold_sale.branch, prefix="FAC").next_number == 2


@pytest.mark.django_db
def test_issue_invoice_applies_confirmed_sale_payment(billing_user, sold_sale):
    invoice = create_invoice_from_sale(
        actor=billing_user,
        sale=sold_sale,
        invoice_type=InvoiceRecord.InvoiceType.INVOICE,
        issue_date=timezone.localdate(),
    )
    issue_invoice(actor=billing_user, invoice=invoice, note="Emitida en prueba")
    invoice.refresh_from_db()
    assert invoice.status == InvoiceRecord.Status.PARTIAL
    assert invoice.amount_paid == Decimal("1000.00")
    assert invoice.balance_due == invoice.total - Decimal("1000.00")


@pytest.mark.django_db
def test_manual_payment_can_mark_invoice_paid(billing_user, sold_sale):
    invoice = create_invoice_from_sale(
        actor=billing_user,
        sale=sold_sale,
        invoice_type=InvoiceRecord.InvoiceType.INVOICE,
        issue_date=timezone.localdate(),
    )
    issue_invoice(actor=billing_user, invoice=invoice)
    invoice.refresh_from_db()
    apply_payment(actor=billing_user, invoice=invoice, amount=invoice.balance_due, notes="Pago final")
    invoice.refresh_from_db()
    assert invoice.status == InvoiceRecord.Status.PAID
    assert invoice.balance_due == Decimal("0.00")


@pytest.mark.django_db
def test_void_invoice_requires_reason_and_changes_status(billing_user, sold_sale):
    invoice = create_invoice_from_sale(
        actor=billing_user,
        sale=sold_sale,
        invoice_type=InvoiceRecord.InvoiceType.INVOICE,
        issue_date=timezone.localdate(),
    )
    void_invoice(actor=billing_user, invoice=invoice, reason="Error de datos")
    invoice.refresh_from_db()
    assert invoice.status == InvoiceRecord.Status.VOID
    assert invoice.void_reason == "Error de datos"


@pytest.mark.django_db
def test_billing_user_can_create_invoice_from_view(client, billing_user, sold_sale):
    client.force_login(billing_user)
    response = client.post(
        "/dashboard/invoices/new/",
        {
            "sale": sold_sale.pk,
            "invoice_type": InvoiceRecord.InvoiceType.INVOICE,
            "issue_date": timezone.localdate().isoformat(),
            "due_date": (timezone.localdate() + timedelta(days=7)).isoformat(),
            "notes": "Desde vista",
            "internal_notes": "Prueba",
        },
    )
    invoice = InvoiceRecord.objects.get(sale=sold_sale)
    assert response.status_code == 302
    assert response.headers["Location"] == f"/dashboard/invoices/{invoice.pk}/"


@pytest.mark.django_db
def test_invoice_detail_and_print_routes_render(client, billing_user, sold_sale):
    invoice = create_invoice_from_sale(
        actor=billing_user,
        sale=sold_sale,
        invoice_type=InvoiceRecord.InvoiceType.INVOICE,
        issue_date=timezone.localdate(),
    )
    client.force_login(billing_user)
    assert client.get(f"/dashboard/invoices/{invoice.pk}/").status_code == 200
    print_response = client.get(f"/dashboard/invoices/{invoice.pk}/print/")
    assert print_response.status_code == 200
    assert invoice.number.encode() in print_response.content


@pytest.mark.django_db
def test_sidebar_points_to_billing_module(client, billing_user):
    client.force_login(billing_user)
    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert b"/dashboard/invoices/" in response.content
    assert b"Facturaci" in response.content
