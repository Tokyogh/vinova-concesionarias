"""ES: Este módulo especifica regresiones ejecutables para el dominio de ventas.

EN: This module specifies executable regressions for the sales domain.

Contexto existente / Existing context:
Regression coverage for commercial integrity v110 in the sales domain.
"""

from datetime import timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.audit.models import AuditLog
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.inventory.models import BranchStock, InventoryCategory, InventoryItem
from apps.sales.forms import SalePaymentForm
from apps.sales.models import SaleLine, SalePayment, SaleRecord
from apps.sales.services import add_sale_payment, cancel_sale, confirm_sale, expire_sale, reserve_sale, void_sale_payment
from apps.sales.tasks import expire_overdue_sales
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel


def commercial_context(django_user_model):
    company = Company.objects.create(legal_name="Integridad S.A.", commercial_name="Integridad", ruc="1799999999001")
    branches = [Branch.objects.create(company=company, name=f"Sucursal {i}", code=f"INT-{i}", city="Quito") for i in (1, 2)]
    permissions = [PermissionCode.objects.create(module="sales", code=code, name=code) for code in ("sales.quote", "sales.reserve", "sales.sell")]
    role = Role.objects.create(code="integridad_comercial", name="Integridad comercial")
    role.permissions.add(*permissions)
    user = django_user_model.objects.create_user(username="integridad", email="integridad@example.com", password="x")
    UserRole.objects.create(user=user, role=role, branch=branches[0])
    customer = Customer.objects.create(first_name="Cliente", identification_number="0999000001", assigned_branch=branches[0])
    brand = VehicleBrand.objects.create(name="Marca Integridad")
    model = VehicleModel.objects.create(brand=brand, name="Modelo Integridad")
    vehicle = Vehicle.objects.create(brand=brand, model=model, branch=branches[0], year=2026, vin="VIN-INTEGRIDAD-1", public_slug="vin-integridad-1", price="100.00")
    return user, branches, customer, vehicle, role


def quote(*, number, customer, branch, vehicle=None, total=Decimal("115.00")):
    return SaleRecord.objects.create(number=number, kind=SaleRecord.Kind.QUOTE, status=SaleRecord.Status.QUOTED, customer=customer, branch=branch, vehicle=vehicle, vehicle_price=Decimal("100.00"), total=total, balance_due=total)


@pytest.mark.django_db
def test_double_reservation_and_sale_are_rejected(django_user_model):
    user, branches, customer, vehicle, _ = commercial_context(django_user_model)
    first = quote(number="COT-I-1", customer=customer, branch=branches[0], vehicle=vehicle)
    second = quote(number="COT-I-2", customer=customer, branch=branches[0], vehicle=vehicle)
    reserve_sale(actor=user, sale=first, reserved_until=timezone.now() + timedelta(hours=1))
    with pytest.raises(ValidationError):
        reserve_sale(actor=user, sale=second, reserved_until=timezone.now() + timedelta(hours=1))
    with pytest.raises(ValidationError):
        confirm_sale(actor=user, sale=second)


@pytest.mark.django_db
def test_reservation_requires_future_expiry(django_user_model):
    user, branches, customer, vehicle, _ = commercial_context(django_user_model)
    sale = quote(number="COT-I-3", customer=customer, branch=branches[0], vehicle=vehicle)
    with pytest.raises(ValidationError):
        reserve_sale(actor=user, sale=sale, reserved_until=None)
    with pytest.raises(ValidationError):
        reserve_sale(actor=user, sale=sale, reserved_until=timezone.now() - timedelta(seconds=1))


@pytest.mark.django_db(transaction=True)
def test_database_constraint_serializes_competing_commitments(django_user_model):
    _, branches, customer, vehicle, _ = commercial_context(django_user_model)
    quote(number="RES-I-1", customer=customer, branch=branches[0], vehicle=vehicle)
    SaleRecord.objects.filter(number="RES-I-1").update(status=SaleRecord.Status.RESERVED, reserved_until=timezone.now() + timedelta(hours=1))
    with pytest.raises(IntegrityError), transaction.atomic():
        SaleRecord.objects.create(number="VEN-I-2", kind=SaleRecord.Kind.SALE, status=SaleRecord.Status.SOLD, customer=customer, branch=branches[0], vehicle=vehicle)


@pytest.mark.django_db
def test_expiry_task_is_idempotent_and_releases_vehicle(django_user_model):
    user, branches, customer, vehicle, _ = commercial_context(django_user_model)
    sale = quote(number="RES-I-3", customer=customer, branch=branches[0], vehicle=vehicle)
    reserve_sale(actor=user, sale=sale, reserved_until=timezone.now() + timedelta(hours=1))
    SaleRecord.objects.filter(pk=sale.pk).update(reserved_until=timezone.now() - timedelta(seconds=1))
    assert expire_overdue_sales()["expired"] == 1
    assert expire_overdue_sales()["expired"] == 0
    sale.refresh_from_db()
    vehicle.refresh_from_db()
    assert sale.status == SaleRecord.Status.EXPIRED
    assert vehicle.status == Vehicle.Status.AVAILABLE


@pytest.mark.django_db
def test_expiry_releases_reserved_inventory_once(django_user_model):
    user, branches, customer, vehicle, _ = commercial_context(django_user_model)
    category = InventoryCategory.objects.create(name="Integridad", slug="integridad")
    item = InventoryItem.objects.create(category=category, name="Repuesto", sku="INT-STOCK", price="10.00")
    stock = BranchStock.objects.create(item=item, branch=branches[0], quantity=Decimal("5.00"))
    sale = quote(number="RES-STOCK-1", customer=customer, branch=branches[0], vehicle=vehicle)
    SaleLine.objects.create(sale=sale, item=item, description=item.name, quantity=Decimal("2.00"), unit_price=item.price, line_subtotal=Decimal("20.00"), line_total=Decimal("20.00"))
    reserve_sale(actor=user, sale=sale, reserved_until=timezone.now() + timedelta(hours=1))
    SaleRecord.objects.filter(pk=sale.pk).update(reserved_until=timezone.now() - timedelta(seconds=1))
    expire_overdue_sales()
    expire_overdue_sales()
    stock.refresh_from_db()
    assert stock.quantity == Decimal("5.00")
    assert stock.reserved_quantity == Decimal("0.00")


@pytest.mark.django_db
def test_confirmed_payment_cannot_overpay(django_user_model):
    user, branches, customer, _, _ = commercial_context(django_user_model)
    sale = quote(number="COT-PAY-1", customer=customer, branch=branches[0], total=Decimal("115.00"))
    form = SalePaymentForm(data={"method": SalePayment.Method.CASH, "status": SalePayment.Status.CONFIRMED, "amount": "116.00", "paid_at": timezone.now().strftime("%Y-%m-%dT%H:%M")})
    assert form.is_valid(), form.errors
    with pytest.raises(ValidationError):
        add_sale_payment(actor=user, sale=sale, form=form)
    assert not sale.payments.exists()


@pytest.mark.django_db
def test_competing_confirmed_payments_are_serialized(django_user_model):
    user, branches, customer, _, _ = commercial_context(django_user_model)
    sale = quote(number="COT-PAY-2", customer=customer, branch=branches[0], total=Decimal("115.00"))
    forms = [SalePaymentForm(data={"method": "cash", "status": "confirmed", "amount": "70.00", "paid_at": timezone.now().strftime("%Y-%m-%dT%H:%M")}) for _ in range(2)]
    assert all(form.is_valid() for form in forms)
    add_sale_payment(actor=user, sale=sale, form=forms[0])
    with pytest.raises(ValidationError):
        add_sale_payment(actor=user, sale=sale, form=forms[1])
    assert sale.payments.filter(status=SalePayment.Status.CONFIRMED).count() == 1


@pytest.mark.django_db
def test_payment_void_is_audited_recalculates_balance_and_is_idempotent(django_user_model):
    user, branches, customer, _, _ = commercial_context(django_user_model)
    sale = quote(number="COT-PAY-VOID-1", customer=customer, branch=branches[0], total=Decimal("115.00"))
    payment = SalePayment.objects.create(
        sale=sale,
        method=SalePayment.Method.TRANSFER,
        status=SalePayment.Status.CONFIRMED,
        amount=Decimal("40.00"),
        received_by=user,
    )
    sale.amount_paid = Decimal("40.00")
    sale.balance_due = Decimal("75.00")
    sale.save(update_fields=["amount_paid", "balance_due", "updated_at"])

    void_sale_payment(actor=user, payment=payment, reason="Transferencia reversada")
    void_sale_payment(actor=user, payment=payment, reason="Reintento idempotente")

    payment.refresh_from_db()
    sale.refresh_from_db()
    assert payment.status == SalePayment.Status.VOID
    assert "Transferencia reversada" in payment.notes
    assert "Reintento idempotente" not in payment.notes
    assert sale.amount_paid == Decimal("0.00")
    assert sale.balance_due == sale.total
    logs = AuditLog.objects.filter(action="sales.payment_void", object_id=str(sale.pk))
    assert logs.count() == 1
    log = logs.get()
    assert log.branch_id == sale.branch_id
    assert log.after == {
        "payment": payment.pk,
        "status": SalePayment.Status.VOID,
        "amount": "40.00",
        "reason": "Transferencia reversada",
    }


@pytest.mark.django_db
def test_payment_void_html_and_api_enforce_reason_scope_and_return_fresh_state(client, django_user_model):
    user, branches, customer, _, _ = commercial_context(django_user_model)
    own_sale = quote(number="COT-PAY-VOID-API-OWN", customer=customer, branch=branches[0])
    own_payment = SalePayment.objects.create(
        sale=own_sale,
        method=SalePayment.Method.CASH,
        status=SalePayment.Status.CONFIRMED,
        amount=Decimal("15.00"),
        received_by=user,
    )
    other_customer = Customer.objects.create(
        first_name="Pago fuera de alcance",
        identification_number="0999000099",
        assigned_branch=branches[1],
    )
    other_sale = quote(number="COT-PAY-VOID-API-OTHER", customer=other_customer, branch=branches[1])
    other_payment = SalePayment.objects.create(
        sale=other_sale,
        method=SalePayment.Method.CASH,
        status=SalePayment.Status.CONFIRMED,
        amount=Decimal("10.00"),
    )
    client.force_login(user)

    missing_reason = client.post(f"/api/v1/sale-payments/{own_payment.pk}/void/", {}, content_type="application/json")
    assert missing_reason.status_code == 400
    own_payment.refresh_from_db()
    assert own_payment.status == SalePayment.Status.CONFIRMED

    outside_scope = client.post(
        f"/api/v1/sale-payments/{other_payment.pk}/void/",
        {"reason": "No autorizado"},
        content_type="application/json",
    )
    assert outside_scope.status_code == 404

    response = client.post(
        f"/api/v1/sale-payments/{own_payment.pk}/void/",
        {"reason": "Reverso confirmado"},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.data["status"] == SalePayment.Status.VOID

    own_payment.status = SalePayment.Status.CONFIRMED
    own_payment.notes = ""
    own_payment.save(update_fields=["status", "notes", "updated_at"])
    html_response = client.post(
        f"/dashboard/sales/{own_sale.pk}/payments/{own_payment.pk}/void/",
        {"reason": "Reverso desde HTML"},
    )
    assert html_response.status_code == 302
    own_payment.refresh_from_db()
    assert own_payment.status == SalePayment.Status.VOID


@pytest.mark.django_db
@pytest.mark.parametrize("transition", [cancel_sale, expire_sale])
def test_active_payment_blocks_terminal_transition_until_explicitly_voided(django_user_model, transition):
    user, branches, customer, _, _ = commercial_context(django_user_model)
    sale = quote(number=f"COT-PAY-{transition.__name__}", customer=customer, branch=branches[0])
    payment = SalePayment.objects.create(
        sale=sale,
        method=SalePayment.Method.CASH,
        status=SalePayment.Status.PENDING,
        amount=Decimal("10.00"),
        received_by=user,
    )

    with pytest.raises(ValidationError):
        transition(actor=user, sale=sale)
    sale.refresh_from_db()
    assert sale.status == SaleRecord.Status.QUOTED

    void_sale_payment(actor=user, payment=payment, reason="Operación descartada")
    transition(actor=user, sale=sale)
    sale.refresh_from_db()
    assert sale.status in {SaleRecord.Status.CANCELLED, SaleRecord.Status.EXPIRED}


def test_new_payment_cannot_be_created_as_void():
    form = SalePaymentForm(
        data={
            "method": SalePayment.Method.CASH,
            "status": SalePayment.Status.VOID,
            "amount": "10.00",
            "paid_at": timezone.now().strftime("%Y-%m-%dT%H:%M"),
        }
    )

    assert not form.is_valid()


@pytest.mark.django_db
def test_payment_admin_is_read_only_and_cannot_bypass_void_service(client, django_user_model):
    user, branches, customer, _, _ = commercial_context(django_user_model)
    user.is_staff = True
    user.is_superuser = True
    user.save(update_fields=["is_staff", "is_superuser"])
    sale = quote(number="COT-PAY-ADMIN-READONLY", customer=customer, branch=branches[0])
    payment = SalePayment.objects.create(
        sale=sale,
        method=SalePayment.Method.CASH,
        status=SalePayment.Status.CONFIRMED,
        amount=Decimal("10.00"),
        received_by=user,
    )
    client.force_login(user)

    response = client.post(
        f"/admin/sales/salepayment/{payment.pk}/change/",
        {"status": SalePayment.Status.VOID, "_save": "Guardar"},
    )

    assert response.status_code == 302
    payment.refresh_from_db()
    assert payment.status == SalePayment.Status.CONFIRMED
    assert not AuditLog.objects.filter(action="sales.payment_void", object_id=str(sale.pk)).exists()
    assert client.get("/admin/sales/salepayment/add/").status_code == 403


@pytest.mark.django_db
def test_branch_scope_applies_to_html_api_and_direct_mutations_are_disabled(client, django_user_model):
    user, branches, customer, _, _ = commercial_context(django_user_model)
    own = quote(number="COT-SCOPE-1", customer=customer, branch=branches[0])
    other_customer = Customer.objects.create(first_name="Otro", identification_number="0999000002", assigned_branch=branches[1])
    other = quote(number="COT-SCOPE-2", customer=other_customer, branch=branches[1])
    client.force_login(user)
    html = client.get("/dashboard/sales/")
    assert own.number.encode() in html.content and other.number.encode() not in html.content
    api = client.get("/api/v1/sales/")
    assert own.number in str(api.data) and other.number not in str(api.data)
    assert client.patch(f"/api/v1/sales/{own.pk}/", {"notes": "bypass"}, content_type="application/json").status_code == 405
    assert client.put(f"/api/v1/sales/{own.pk}/", {"notes": "bypass"}, content_type="application/json").status_code == 405
    assert client.delete(f"/api/v1/sales/{own.pk}/").status_code == 405


@pytest.mark.django_db
def test_future_and_expired_roles_do_not_grant_permissions(django_user_model):
    user, branches, _, _, role = commercial_context(django_user_model)
    assignment = UserRole.objects.get(user=user, role=role)
    assignment.starts_at = timezone.now() + timedelta(days=1)
    assignment.save()
    assert not user.has_perm_code("sales.quote", branch=branches[0])
    assignment.starts_at = None
    assignment.expires_at = timezone.now() - timedelta(seconds=1)
    assignment.save()
    assert not user.has_perm_code("sales.quote", branch=branches[0])


@pytest.mark.django_db
def test_commercial_integrity_command_is_read_only_on_clean_data():
    output = StringIO()
    call_command("check_commercial_integrity", stdout=output)
    assert "validada" in output.getvalue().lower()
