"""ES: Este módulo especifica regresiones ejecutables para el dominio de facturación.

EN: This module specifies executable regressions for the invoices domain.

Contexto existente / Existing context:
Regression coverage for invoice branch scope in the invoices domain.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.invoices.models import InvoiceRecord
from apps.invoices.services import apply_payment, create_invoice_from_sale, issue_invoice, void_invoice
from apps.sales.models import SaleLine, SaleRecord
from apps.sales.services import recalculate_sale_totals
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel

pytestmark = pytest.mark.django_db

SALE_COUNT = [0]


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
    ]:
        perms[code] = PermissionCode.objects.create(module=code.split(".")[0], code=code, name=code)
    return perms


def make_branch(company, name, code):
    return Branch.objects.create(
        company=company, name=name, code=code, branch_type=Branch.BranchType.DEALERSHIP, city="Quito"
    )


def make_user(django_user_model, username, password="x12345"):
    return django_user_model.objects.create_user(username=username, email=f"{username}@example.com", password=password)


@pytest.fixture
def cross_branch_scope(django_user_model, invoice_permissions):
    company = Company.objects.create(
        legal_name="Facturación Scope S.A.", commercial_name="Factsco", ruc="1799999999001"
    )
    branch_a = make_branch(company, "Norte Facturación", "INV-A")
    branch_b = make_branch(company, "Sur Facturación", "INV-B")
    billing_role = Role.objects.create(code="facturacion-scope", name="Facturación scope")
    billing_role.permissions.add(*invoice_permissions.values())
    user_a = make_user(django_user_model, "billing-a")
    user_b = make_user(django_user_model, "billing-b")
    global_user = make_user(django_user_model, "billing-global")
    UserRole.objects.create(user=user_a, role=billing_role, branch=branch_a)
    UserRole.objects.create(user=user_b, role=billing_role, branch=branch_b)
    UserRole.objects.create(user=global_user, role=billing_role)
    return branch_a, branch_b, user_a, global_user


def make_sold_sale(branch, customer, user):
    SALE_COUNT[0] += 1
    seq = SALE_COUNT[0]
    brand = VehicleBrand.objects.create(name=f"Brand {branch.code}-{seq}")
    model = VehicleModel.objects.create(brand=brand, name=f"Model {branch.code}-{seq}")
    vehicle = Vehicle.objects.create(
        brand=brand,
        model=model,
        branch=branch,
        year=2024,
        version="SRV",
        vin=f"VININV{branch.code}{seq}",
        public_slug=f"inv-{branch.code.lower()}-{seq}",
        status=Vehicle.Status.SOLD,
        price="40000.00",
    )
    sale = SaleRecord.objects.create(
        number=f"VEN-INV-{branch.code}-{seq:04d}",
        kind=SaleRecord.Kind.SALE,
        status=SaleRecord.Status.SOLD,
        customer=customer,
        branch=branch,
        advisor=user,
        vehicle=vehicle,
        vehicle_price=Decimal("40000.00"),
        vehicle_discount=Decimal("0.00"),
        tax_rate=Decimal("15.00"),
    )
    line = SaleLine.objects.create(
        sale=sale,
        description=f"Kit {branch.code}",
        quantity=Decimal("1.00"),
        unit_price=Decimal("200.00"),
        discount_amount=Decimal("0.00"),
    )
    line.calculate_totals()
    line.save()
    recalculate_sale_totals(sale)
    return sale


def make_invoice(actor, sale, invoice_type=InvoiceRecord.InvoiceType.INVOICE):
    return create_invoice_from_sale(
        actor=actor,
        sale=sale,
        invoice_type=invoice_type,
        issue_date=timezone.localdate(),
    )


@pytest.fixture
def invoices_in_both_branches(cross_branch_scope, django_user_model):
    branch_a, branch_b, user_a, global_user = cross_branch_scope
    customer_a = Customer.objects.create(
        first_name="Ana", last_name="Scope", identification_number="0900000001", assigned_branch=branch_a
    )
    customer_b = Customer.objects.create(
        first_name="Beto", last_name="Scope", identification_number="0900000002", assigned_branch=branch_b
    )
    sale_a = make_sold_sale(branch_a, customer_a, user_a)
    sale_b = make_sold_sale(branch_b, customer_b, user_a)
    invoice_a = make_invoice(user_a, sale_a)
    invoice_b = make_invoice(global_user, sale_b)
    return branch_a, branch_b, user_a, invoice_a, invoice_b, sale_a, sale_b


def test_invoice_list_is_branch_scoped(client, invoices_in_both_branches):
    branch_a, branch_b, user_a, invoice_a, invoice_b, sale_a, sale_b = invoices_in_both_branches
    client.force_login(user_a)

    response = client.get("/dashboard/invoices/")
    assert response.status_code == 200
    content = response.content.decode()
    assert f"/dashboard/invoices/{invoice_a.pk}/" in content
    assert f"/dashboard/invoices/{invoice_b.pk}/" not in content


def test_invoice_detail_and_print_direct_other_branch(client, invoices_in_both_branches):
    branch_a, branch_b, user_a, invoice_a, invoice_b, sale_a, sale_b = invoices_in_both_branches
    client.force_login(user_a)

    assert client.get(f"/dashboard/invoices/{invoice_b.pk}/").status_code == 404
    assert client.get(f"/dashboard/invoices/{invoice_b.pk}/print/").status_code == 404


def test_invoice_mutations_direct_other_branch(client, invoices_in_both_branches):
    branch_a, branch_b, user_a, invoice_a, invoice_b, sale_a, sale_b = invoices_in_both_branches
    client.force_login(user_a)

    assert client.post(f"/dashboard/invoices/{invoice_b.pk}/action/issue/", {"note": "x"}).status_code == 404
    assert client.post(f"/dashboard/invoices/{invoice_b.pk}/action/void/", {"reason": "x"}).status_code == 404
    assert client.post(f"/dashboard/invoices/{invoice_b.pk}/payments/apply/", {"amount": "10.00"}).status_code == 404


def test_invoice_services_reject_other_branch_actor(cross_branch_scope, invoices_in_both_branches):
    branch_a, branch_b, user_a, invoice_a, invoice_b, sale_a, sale_b = invoices_in_both_branches

    with pytest.raises(ValidationError):
        create_invoice_from_sale(
            actor=user_a,
            sale=sale_b,
            invoice_type=InvoiceRecord.InvoiceType.INVOICE,
            issue_date=timezone.localdate(),
        )
    with pytest.raises(ValidationError):
        issue_invoice(actor=user_a, invoice=invoice_b)
    with pytest.raises(ValidationError):
        apply_payment(actor=user_a, invoice=invoice_b, amount=Decimal("10.00"))
    with pytest.raises(ValidationError):
        void_invoice(actor=user_a, invoice=invoice_b, reason="fuera de scope")


@pytest.mark.parametrize("actor", [None, AnonymousUser()])
def test_invoice_services_deny_missing_or_anonymous_actor(actor, invoices_in_both_branches):
    branch_a, branch_b, user_a, invoice_a, invoice_b, sale_a, sale_b = invoices_in_both_branches

    with pytest.raises(ValidationError, match="autenticarte"):
        issue_invoice(actor=actor, invoice=invoice_a)

    invoice_a.refresh_from_db()
    assert invoice_a.status == InvoiceRecord.Status.DRAFT


def test_global_user_keeps_full_scope(cross_branch_scope, invoices_in_both_branches):
    branch_a, branch_b, user_a, invoice_a, invoice_b, sale_a, sale_b = invoices_in_both_branches
    _, _, _, global_user = cross_branch_scope

    issue_invoice(actor=global_user, invoice=invoice_b)
    invoice_b.refresh_from_db()
    assert invoice_b.status == InvoiceRecord.Status.ISSUED
    assert create_invoice_from_sale(
        actor=global_user,
        sale=sale_a,
        invoice_type=InvoiceRecord.InvoiceType.INVOICE,
        issue_date=timezone.localdate(),
    ).branch_id == branch_a.pk


def test_ready_sales_and_api_scoped(client, invoices_in_both_branches, django_user_model):
    branch_a, branch_b, user_a, invoice_a, invoice_b, sale_a, sale_b = invoices_in_both_branches
    customer_a = Customer.objects.create(
        first_name="Ready", last_name="A", identification_number="0900000010", assigned_branch=branch_a
    )
    customer_b = Customer.objects.create(
        first_name="Ready", last_name="B", identification_number="0900000011", assigned_branch=branch_b
    )
    ready_a = make_sold_sale(branch_a, customer_a, user_a)
    ready_b = make_sold_sale(branch_b, customer_b, user_a)
    client.force_login(user_a)

    page = client.get("/dashboard/invoices/new/")
    assert page.status_code == 200
    assert ready_a.number.encode() in page.content
    assert ready_b.number.encode() not in page.content

    api_invoices = client.get("/api/invoices/")
    assert api_invoices.status_code == 200
    api_ids = {item["id"] for item in api_invoices.json()["results"]}
    assert invoice_a.pk in api_ids
    assert invoice_b.pk not in api_ids

    api_ready = client.get("/api/invoices/ready-sales/")
    assert {item["id"] for item in api_ready.json()} == {ready_a.pk}

    assert client.get(f"/api/invoices/{invoice_b.pk}/").status_code == 404


def test_invoice_metrics_scoped(client, invoices_in_both_branches):
    branch_a, branch_b, user_a, invoice_a, invoice_b, sale_a, sale_b = invoices_in_both_branches
    client.force_login(user_a)

    response = client.get("/api/invoices/metrics/")
    assert response.status_code == 200
    assert response.json()["draft"] == 1
    assert response.json()["month_total"] == invoice_a.total


def test_invoice_lines_sequence_history_api_scoped(client, invoices_in_both_branches):
    branch_a, branch_b, user_a, invoice_a, invoice_b, sale_a, sale_b = invoices_in_both_branches
    client.force_login(user_a)

    other_lines = client.get("/api/invoice-lines/", {"invoice": invoice_b.pk})
    assert other_lines.json()["results"] == []

    other_history = client.get("/api/invoice-status-history/", {"invoice": invoice_b.pk})
    assert other_history.json()["results"] == []

    other_apps = client.get("/api/invoice-payments/", {"invoice": invoice_b.pk})
    assert other_apps.json()["results"] == []

    sequences = client.get("/api/invoice-sequences/")
    seq_branch_ids = {item["branch"] for item in sequences.json()["results"]}
    assert branch_b.pk not in seq_branch_ids


def _role(**kwargs):
    return Role.objects.create(**kwargs)


@pytest.fixture
def mixed_action_scope(django_user_model, invoice_permissions):
    """Usuario con invoices.view global + invoices.issue solo en A."""
    company = Company.objects.create(
        legal_name="Mixta Scope S.A.", commercial_name="MixtaScope", ruc="1799999999002"
    )
    branch_a = make_branch(company, "Mixta Norte", "MIX-A")
    branch_b = make_branch(company, "Mixta Sur", "MIX-B")
    view_role = _role(code="view-global", name="Lectura global")
    view_role.permissions.add(invoice_permissions["invoices.view"])
    issue_a_role = _role(code="issue-a", name="Emisión A")
    issue_a_role.permissions.add(invoice_permissions["invoices.issue"])
    user = make_user(django_user_model, "view-global-issue-a")
    UserRole.objects.create(user=user, role=view_role)
    UserRole.objects.create(user=user, role=issue_a_role, branch=branch_a)
    global_billing = _role(code="mixta-global-billing", name="Facturación global")
    global_billing.permissions.add(*invoice_permissions.values())
    global_actor = make_user(django_user_model, "mixta-seller")
    UserRole.objects.create(user=global_actor, role=global_billing)
    return branch_a, branch_b, user, global_actor


def _mixed_invoices(mixed_action_scope):
    branch_a, branch_b, user, global_actor = mixed_action_scope
    customer_a = Customer.objects.create(
        first_name="Ana", last_name="Mixta", identification_number="0900000020", assigned_branch=branch_a
    )
    customer_b = Customer.objects.create(
        first_name="Beto", last_name="Mixta", identification_number="0900000021", assigned_branch=branch_b
    )
    sale_a = make_sold_sale(branch_a, customer_a, global_actor)
    sale_b = make_sold_sale(branch_b, customer_b, global_actor)
    invoice_a = make_invoice(global_actor, sale_a)
    invoice_b = make_invoice(global_actor, sale_b)
    return user, global_actor, sale_a, sale_b, invoice_a, invoice_b


def test_view_global_with_issue_a_cannot_issue_other_branch(mixed_action_scope):
    user, global_actor, sale_a, sale_b, invoice_a, invoice_b = _mixed_invoices(mixed_action_scope)

    with pytest.raises(ValidationError):
        issue_invoice(actor=user, invoice=invoice_b)
    with pytest.raises(ValidationError):
        create_invoice_from_sale(
            actor=user,
            sale=sale_b,
            invoice_type=InvoiceRecord.InvoiceType.INVOICE,
            issue_date=timezone.localdate(),
        )

    issue_invoice(actor=user, invoice=invoice_a)
    invoice_a.refresh_from_db()
    assert invoice_a.status == InvoiceRecord.Status.ISSUED


def test_view_global_with_issue_a_http_mutations_blocked_on_b(client, mixed_action_scope):
    user, global_actor, sale_a, sale_b, invoice_a, invoice_b = _mixed_invoices(mixed_action_scope)
    client.force_login(user)

    detail = client.get(f"/dashboard/invoices/{invoice_b.pk}/")
    assert detail.status_code == 200

    resp = client.post(f"/dashboard/invoices/{invoice_b.pk}/action/issue/", {"note": "x"})
    assert resp.status_code == 302
    invoice_b.refresh_from_db()
    assert invoice_b.status == InvoiceRecord.Status.DRAFT

    lines_before = invoice_b.lines.count()
    client.post(
        f"/dashboard/invoices/{invoice_b.pk}/lines/",
        {"description": "Línea ajena", "quantity": "1.00", "unit_price": "10.00", "discount_amount": "0.00", "tax_rate": "0.00"},
    )
    assert invoice_b.lines.count() == lines_before

    client.post(f"/dashboard/invoices/{invoice_b.pk}/action/void/", {"reason": "sin permiso"})
    invoice_b.refresh_from_db()
    assert invoice_b.status == InvoiceRecord.Status.DRAFT


def test_issue_global_keeps_global_issue_scope(mixed_action_scope, django_user_model, invoice_permissions):
    branch_a, branch_b, user, global_actor = mixed_action_scope
    customer_b = Customer.objects.create(
        first_name="Global", last_name="Emisor", identification_number="0900000022", assigned_branch=branch_b
    )
    sale_b = make_sold_sale(branch_b, customer_b, global_actor)
    invoice_b = make_invoice(global_actor, sale_b)

    issue_global_role = _role(code="issue-global", name="Emisión global")
    issue_global_role.permissions.add(invoice_permissions["invoices.issue"])
    issue_global = make_user(django_user_model, "issue-global")
    UserRole.objects.create(user=issue_global, role=issue_global_role)

    issue_invoice(actor=issue_global, invoice=invoice_b)
    invoice_b.refresh_from_db()
    assert invoice_b.status == InvoiceRecord.Status.ISSUED
    assert (
        create_invoice_from_sale(
            actor=issue_global,
            sale=sale_b,
            invoice_type=InvoiceRecord.InvoiceType.INVOICE,
            issue_date=timezone.localdate(),
        ).branch_id
        == branch_b.pk
    )


def test_branch_only_actor_cannot_touch_other_branch(mixed_action_scope, django_user_model, invoice_permissions):
    branch_a, branch_b, user, global_actor = mixed_action_scope
    customer_a = Customer.objects.create(
        first_name="Solo", last_name="A", identification_number="0900000023", assigned_branch=branch_a
    )
    customer_b = Customer.objects.create(
        first_name="Solo", last_name="B", identification_number="0900000024", assigned_branch=branch_b
    )
    sale_a = make_sold_sale(branch_a, customer_a, global_actor)
    sale_b = make_sold_sale(branch_b, customer_b, global_actor)
    invoice_a = make_invoice(global_actor, sale_a)
    invoice_b = make_invoice(global_actor, sale_b)

    issue_a_only_role = _role(code="issue-a-only", name="Emisión solo A")
    issue_a_only_role.permissions.add(invoice_permissions["invoices.issue"])
    issue_a_only = make_user(django_user_model, "issue-a-only")
    UserRole.objects.create(user=issue_a_only, role=issue_a_only_role, branch=branch_a)

    with pytest.raises(ValidationError):
        create_invoice_from_sale(
            actor=issue_a_only,
            sale=sale_b,
            invoice_type=InvoiceRecord.InvoiceType.INVOICE,
            issue_date=timezone.localdate(),
        )
    with pytest.raises(ValidationError):
        issue_invoice(actor=issue_a_only, invoice=invoice_b)
    assert (
        create_invoice_from_sale(
            actor=issue_a_only,
            sale=sale_a,
            invoice_type=InvoiceRecord.InvoiceType.INVOICE,
            issue_date=timezone.localdate(),
        ).branch_id
        == branch_a.pk
    )

    issue_invoice(actor=issue_a_only, invoice=invoice_a)
    invoice_a.refresh_from_db()
    assert invoice_a.status == InvoiceRecord.Status.ISSUED


def test_view_global_with_issue_a_payment_scope(client, mixed_action_scope):
    user, global_actor, sale_a, sale_b, invoice_a, invoice_b = _mixed_invoices(mixed_action_scope)
    issue_invoice(actor=global_actor, invoice=invoice_a)
    issue_invoice(actor=global_actor, invoice=invoice_b)
    invoice_a.refresh_from_db()
    invoice_b.refresh_from_db()
    assert invoice_a.status == InvoiceRecord.Status.ISSUED
    with pytest.raises(ValidationError):
        apply_payment(actor=user, invoice=invoice_b, amount=Decimal("10.00"))
    apply_payment(actor=user, invoice=invoice_a, amount=Decimal("10.00"))
    invoice_a.refresh_from_db()
    assert invoice_a.amount_paid == Decimal("10.00")


def test_manage_scope_acts_as_superset_for_issue_and_void(mixed_action_scope, django_user_model, invoice_permissions):
    branch_a, branch_b, user, global_actor = mixed_action_scope
    customer_a = Customer.objects.create(
        first_name="Mgr", last_name="A", identification_number="0900000025", assigned_branch=branch_a
    )
    customer_b = Customer.objects.create(
        first_name="Mrg", last_name="B", identification_number="0900000026", assigned_branch=branch_b
    )
    sale_a = make_sold_sale(branch_a, customer_a, global_actor)
    sale_b = make_sold_sale(branch_b, customer_b, global_actor)
    invoice_a = make_invoice(global_actor, sale_a)
    invoice_b = make_invoice(global_actor, sale_b)

    manage_a_role = _role(code="manage-a", name="Gestión A")
    manage_a_role.permissions.add(invoice_permissions["invoices.manage"])
    manager_a = make_user(django_user_model, "manager-a")
    UserRole.objects.create(user=manager_a, role=manage_a_role, branch=branch_a)

    issue_invoice(actor=manager_a, invoice=invoice_a)
    void_invoice(actor=manager_a, invoice=invoice_a, reason="prueba")
    invoice_a.refresh_from_db()
    assert invoice_a.status == InvoiceRecord.Status.VOID

    with pytest.raises(ValidationError):
        issue_invoice(actor=manager_a, invoice=invoice_b)
    with pytest.raises(ValidationError):
        void_invoice(actor=manager_a, invoice=invoice_b, reason="fuera de scope")
