"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de ventas.

EN: This module implements business services and transactional effects for the sales domain.

Contexto existente / Existing context:
Transactional business services for the sales domain.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

from apps.audit.services import audit_log
from apps.common.db_locks import acquire_transaction_advisory_lock
from apps.inventory.models import BranchStock, StockMovement
from apps.sales.models import SaleLine, SalePayment, SaleRecord, SaleStatusHistory
from apps.vehicles.models import Vehicle


def _money(value) -> Decimal:
    return Decimal(value or 0).quantize(Decimal("0.01"))


def _sale_snapshot(sale: SaleRecord) -> dict:
    return {
        "number": sale.number,
        "kind": sale.kind,
        "status": sale.status,
        "customer": sale.customer_id,
        "branch": sale.branch_id,
        "advisor": sale.advisor_id,
        "vehicle": sale.vehicle_id,
        "vehicle_price": str(sale.vehicle_price),
        "total": str(sale.total),
        "amount_paid": str(sale.amount_paid),
        "balance_due": str(sale.balance_due),
    }


def _line_snapshot(line: SaleLine) -> dict:
    return {
        "sale": line.sale_id,
        "item": line.item_id,
        "description": line.description,
        "quantity": str(line.quantity),
        "unit_price": str(line.unit_price),
        "discount_amount": str(line.discount_amount),
        "line_total": str(line.line_total),
        "reserved_quantity": str(line.reserved_quantity),
        "fulfilled_quantity": str(line.fulfilled_quantity),
    }


def generate_sale_number(kind: str) -> str:
    prefix_map = {SaleRecord.Kind.QUOTE: "COT", SaleRecord.Kind.RESERVATION: "RES", SaleRecord.Kind.SALE: "VEN"}
    prefix = prefix_map.get(kind, "COM")
    today = timezone.localdate()
    base = f"{prefix}-{today:%Y%m%d}"
    acquire_transaction_advisory_lock(namespace="sale-number", value=base)
    count = SaleRecord.objects.filter(number__startswith=base).count() + 1
    candidate = f"{base}-{count:04d}"
    while SaleRecord.objects.filter(number=candidate).exists():
        count += 1
        candidate = f"{base}-{count:04d}"
    return candidate


def _initial_status_for_kind(kind: str) -> str:
    # Una reserva creada desde formulario inicia como cotización y después pasa
    # por reserve_sale(), para ejecutar las mismas validaciones de vehículo y stock.
    if kind == SaleRecord.Kind.SALE:
        return SaleRecord.Status.APPROVED
    return SaleRecord.Status.QUOTED


@transaction.atomic
def create_sale_from_data(*, actor, validated_data: dict, history_note: str = "Operación creada") -> SaleRecord:
    """ES: Ejecuta la operación «create sale from data» dentro del dominio de ventas. Además, aplica autorización en backend, rechaza estados o entradas inválidas.

    EN: Executes the «create sale from data» operation within the sales domain. It also enforces server-side authorization, rejects invalid input or state.
    """

    sale = SaleRecord(**validated_data)
    sale.number = generate_sale_number(sale.kind)
    sale.status = _initial_status_for_kind(sale.kind)
    sale.created_by = actor if getattr(actor, "is_authenticated", False) else None
    if not sale.advisor_id and sale.created_by:
        sale.advisor = actor
    if actor is not None and not actor.has_perm_code("sales.quote", branch=sale.branch):
        raise ValidationError("No tienes permiso para crear operaciones en esta sucursal.")
    if sale.customer.assigned_branch_id not in (None, sale.branch_id):
        raise ValidationError("El cliente está asignado a otra sucursal.")
    if sale.vehicle_id:
        if sale.vehicle.branch_id != sale.branch_id or sale.vehicle.status != Vehicle.Status.AVAILABLE:
            raise ValidationError("El vehículo no está disponible en esta sucursal.")
        if not sale.vehicle_price:
            sale.vehicle_price = sale.vehicle.price or Decimal("0.00")
    sale.full_clean()
    sale.save()
    create_status_history(sale=sale, new=sale.status, actor=actor, note=history_note)
    recalculate_sale_totals(sale)
    if sale.kind == SaleRecord.Kind.RESERVATION:
        return reserve_sale(actor=actor, sale=sale, reserved_until=sale.reserved_until, note=history_note)
    return sale


def create_status_history(*, sale: SaleRecord, previous: str = "", new: str, actor=None, note: str = "", metadata: dict | None = None):
    return SaleStatusHistory.objects.create(
        sale=sale,
        previous_status=previous or "",
        new_status=new,
        changed_by=actor if getattr(actor, "is_authenticated", False) else None,
        note=note,
        metadata=metadata or {},
    )


@transaction.atomic
def recalculate_sale_totals(sale: SaleRecord) -> SaleRecord:
    lines = sale.lines.all()
    for line in lines:
        line.calculate_totals()
        line.save(update_fields=["line_subtotal", "line_total", "updated_at"])
    line_subtotal = sale.lines.aggregate(total=Sum("line_subtotal"))["total"] or Decimal("0.00")
    line_total = sale.lines.aggregate(total=Sum("line_total"))["total"] or Decimal("0.00")
    vehicle_net = max(_money(sale.vehicle_price) - _money(sale.vehicle_discount), Decimal("0.00"))
    sale.line_subtotal = _money(line_subtotal)
    sale.discount_total = _money(sale.vehicle_discount) + max(_money(line_subtotal) - _money(line_total), Decimal("0.00"))
    sale.subtotal = _money(vehicle_net + _money(line_total))
    sale.tax_total = _money(sale.subtotal * (_money(sale.tax_rate) / Decimal("100")))
    sale.total = _money(sale.subtotal + sale.tax_total)
    sale.amount_paid = _money(sale.payments.filter(status=SalePayment.Status.CONFIRMED).aggregate(total=Sum("amount"))["total"] or Decimal("0.00"))
    sale.balance_due = max(_money(sale.total) - _money(sale.amount_paid), Decimal("0.00"))
    sale.save(update_fields=["line_subtotal", "discount_total", "subtotal", "tax_total", "total", "amount_paid", "balance_due", "updated_at"])
    return sale


@transaction.atomic
def create_sale(*, actor, form) -> SaleRecord:
    sale = form.save(commit=False)
    if actor is not None and not actor.has_perm_code("sales.quote", branch=sale.branch):
        raise ValidationError("No tienes permiso para crear operaciones en esta sucursal.")
    if sale.customer.assigned_branch_id not in (None, sale.branch_id):
        raise ValidationError("El cliente está asignado a otra sucursal.")
    sale.number = generate_sale_number(sale.kind)
    sale.status = _initial_status_for_kind(sale.kind)
    sale.created_by = actor if getattr(actor, "is_authenticated", False) else None
    if sale.advisor_id is None and getattr(actor, "is_authenticated", False):
        sale.advisor = actor
    if sale.vehicle and not sale.vehicle_price:
        sale.vehicle_price = sale.vehicle.price or Decimal("0.00")
    sale.full_clean()
    sale.save()
    create_status_history(sale=sale, new=sale.status, actor=actor, note="Operación creada")
    recalculate_sale_totals(sale)
    audit_log(user=actor, action="sales.create", target=sale, after=_sale_snapshot(sale))
    if sale.kind == SaleRecord.Kind.RESERVATION:
        reserve_sale(actor=actor, sale=sale, reserved_until=sale.reserved_until, note="Reserva creada desde formulario")
    return sale


@transaction.atomic
def update_sale(*, actor, sale: SaleRecord, form) -> SaleRecord:
    sale = _locked_sale(sale)
    if actor is not None and not actor.has_perm_code("sales.quote", branch=sale.branch):
        raise ValidationError("No tienes permiso para editar operaciones en esta sucursal.")
    if sale.is_closed or sale.status == SaleRecord.Status.RESERVED:
        raise ValidationError("No se puede editar una operación cerrada.")
    before = _sale_snapshot(sale)
    sale = form.save(commit=False)
    if sale.vehicle and not sale.vehicle_price:
        sale.vehicle_price = sale.vehicle.price or Decimal("0.00")
    sale.full_clean()
    sale.save()
    recalculate_sale_totals(sale)
    audit_log(user=actor, action="sales.update", target=sale, before=before, after=_sale_snapshot(sale))
    return sale


@transaction.atomic
def add_sale_line(*, actor, sale: SaleRecord, form) -> SaleLine:
    sale = _locked_sale(sale)
    if actor is not None and not actor.has_perm_code("sales.quote", branch=sale.branch):
        raise ValidationError("No tienes permiso para editar operaciones en esta sucursal.")
    if sale.is_closed:
        raise ValidationError("No se pueden agregar líneas a una operación cerrada.")
    line = form.save(commit=False)
    line.sale = sale
    if line.item and not line.description:
        line.description = line.item.name
    if line.item and not line.unit_price:
        line.unit_price = line.item.price
    line.calculate_totals()
    line.full_clean()
    line.save()
    recalculate_sale_totals(sale)
    audit_log(user=actor, action="sales.line_add", target=sale, after=_line_snapshot(line))
    return line


@transaction.atomic
def add_sale_payment(*, actor, sale: SaleRecord, form) -> SalePayment:
    sale = SaleRecord.objects.select_for_update().select_related("branch").get(pk=sale.pk)
    if actor is not None and not actor.has_perm_code("sales.sell", branch=sale.branch):
        raise ValidationError("No tienes permiso para registrar pagos en esta sucursal.")
    if sale.status in {SaleRecord.Status.CANCELLED, SaleRecord.Status.VOID, SaleRecord.Status.EXPIRED}:
        raise ValidationError("No se pueden registrar pagos en una operación cancelada, anulada o expirada.")
    payment = form.save(commit=False)
    payment.sale = sale
    payment.received_by = actor if getattr(actor, "is_authenticated", False) else None
    if payment.status == SalePayment.Status.VOID:
        raise ValidationError("Un pago nuevo no puede registrarse directamente como anulado.")
    payment.full_clean()
    if payment.status == SalePayment.Status.CONFIRMED:
        recalculate_sale_totals(sale)
        if sale.total <= 0:
            raise ValidationError("No se puede confirmar un pago en una operación sin total calculado.")
        if _money(payment.amount) > _money(sale.balance_due):
            raise ValidationError("El pago confirmado supera el saldo pendiente de la operación.")
    payment.save()
    recalculate_sale_totals(sale)
    audit_log(user=actor, action="sales.payment_add", target=sale, after={"amount": str(payment.amount), "method": payment.method, "status": payment.status})
    return payment


@transaction.atomic
def void_sale_payment(*, actor, payment: SalePayment, reason: str) -> SalePayment:
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError("Registra el motivo de anulación del pago.")

    # Keep the same lock order used when a payment is created: sale first,
    # payment second. This serializes reversals against additions/cancellation.
    sale = _locked_sale(payment.sale)
    if actor is not None and not actor.has_perm_code("sales.sell", branch=sale.branch):
        raise ValidationError("No tienes permiso para anular pagos en esta sucursal.")
    payment = SalePayment.objects.select_for_update().get(pk=payment.pk, sale=sale)
    if payment.status == SalePayment.Status.VOID:
        return payment

    previous = payment.status
    payment.status = SalePayment.Status.VOID
    payment.notes = "\n".join(
        part for part in [payment.notes.strip(), f"Anulado: {reason}"] if part
    )
    payment.save(update_fields=["status", "notes", "updated_at"])
    recalculate_sale_totals(sale)
    audit_log(
        user=actor,
        action="sales.payment_void",
        target=sale,
        branch=sale.branch,
        before={"payment": payment.pk, "status": previous, "amount": str(payment.amount)},
        after={
            "payment": payment.pk,
            "status": payment.status,
            "amount": str(payment.amount),
            "reason": reason,
        },
    )
    return payment


def _stock_record_for_update(*, item, branch):
    record = BranchStock.objects.select_for_update().filter(item=item, branch=branch).first()
    if record:
        return record
    try:
        with transaction.atomic():
            return BranchStock.objects.create(item=item, branch=branch)
    except IntegrityError:
        return BranchStock.objects.select_for_update().get(item=item, branch=branch)


def _locked_sale(sale: SaleRecord) -> SaleRecord:
    return SaleRecord.objects.select_for_update().get(pk=sale.pk, is_deleted=False)


def _sync_origin_leads(*, actor, sale: SaleRecord) -> int:
    # Local import avoids a module cycle: leads.services creates sales through
    # this module, while this callback updates the originating CRM records.
    from apps.leads.sale_lifecycle import sync_origin_leads_for_sale

    return sync_origin_leads_for_sale(actor=actor, sale=sale)


def _vehicle_conflict(*, sale: SaleRecord, vehicle: Vehicle):
    return SaleRecord.objects.select_for_update().filter(
        vehicle=vehicle,
        is_deleted=False,
        status__in=[SaleRecord.Status.RESERVED, SaleRecord.Status.SOLD],
    ).exclude(pk=sale.pk).first()


@transaction.atomic
def reserve_sale(*, actor, sale: SaleRecord, reserved_until=None, note: str = "") -> SaleRecord:
    """Reserve an eligible sale under a row lock and authorized branch scope."""

    sale = _locked_sale(sale)
    if actor is not None and not actor.has_perm_code("sales.reserve", branch=sale.branch):
        raise ValidationError("No tienes permiso para reservar en esta sucursal.")
    if not sale.can_be_reserved:
        raise ValidationError("Esta operación no puede pasar a reserva desde su estado actual.")
    if not reserved_until:
        raise ValidationError("Toda reserva debe tener una fecha de vencimiento.")
    if reserved_until <= timezone.now():
        raise ValidationError("La reserva debe vencer en una fecha futura.")
    if sale.vehicle:
        vehicle = Vehicle.objects.select_for_update().get(pk=sale.vehicle_id, is_deleted=False)
        conflict = _vehicle_conflict(sale=sale, vehicle=vehicle)
        if conflict:
            raise ValidationError(f"La unidad ya está comprometida por la operación {conflict.number}.")
        if vehicle.status != Vehicle.Status.AVAILABLE:
            raise ValidationError("El vehículo no está disponible para reserva.")
        vehicle.status = Vehicle.Status.RESERVED
        vehicle.save(update_fields=["status", "updated_at"])

    for line in sale.lines.select_for_update():
        if not line.item or not line.item.track_stock:
            continue
        stock = _stock_record_for_update(item=line.item, branch=sale.branch)
        available = stock.quantity - stock.reserved_quantity
        to_reserve = line.quantity - line.reserved_quantity
        if to_reserve <= 0:
            continue
        if available < to_reserve:
            raise ValidationError(f"Stock insuficiente para reservar {line.item.sku} en {sale.branch.name}.")
        stock.reserved_quantity += to_reserve
        stock.save(update_fields=["reserved_quantity", "updated_at"])
        line.reserved_quantity += to_reserve
        line.save(update_fields=["reserved_quantity", "updated_at"])
        StockMovement.objects.create(
            item=line.item,
            branch=sale.branch,
            movement_type=StockMovement.MovementType.RESERVE,
            quantity=to_reserve,
            previous_quantity=stock.quantity,
            new_quantity=stock.quantity,
            reference=sale.number,
            reason=note or "Reserva comercial",
            created_by=actor if getattr(actor, "is_authenticated", False) else None,
            confirmed_at=timezone.now(),
        )

    previous = sale.status
    sale.kind = SaleRecord.Kind.RESERVATION
    sale.status = SaleRecord.Status.RESERVED
    sale.reserved_until = reserved_until
    sale.full_clean()
    try:
        with transaction.atomic():
            sale.save(update_fields=["kind", "status", "reserved_until", "updated_at"])
    except IntegrityError as exc:
        raise ValidationError("La unidad fue comprometida por otra operación concurrente.") from exc
    create_status_history(sale=sale, previous=previous, new=sale.status, actor=actor, note=note)
    audit_log(user=actor, action="sales.reserve", target=sale, before={"status": previous}, after=_sale_snapshot(sale))
    _sync_origin_leads(actor=actor, sale=sale)
    return sale


@transaction.atomic
def release_sale_reservations(*, actor, sale: SaleRecord, note: str = "") -> None:
    sale = _locked_sale(sale)
    if sale.vehicle_id:
        vehicle = Vehicle.objects.select_for_update().get(pk=sale.vehicle_id)
        conflict = _vehicle_conflict(sale=sale, vehicle=vehicle)
        if conflict:
            raise ValidationError(f"No se liberó la unidad porque existe otra operación activa: {conflict.number}.")
        if vehicle.status == Vehicle.Status.RESERVED:
            vehicle.status = Vehicle.Status.AVAILABLE
            vehicle.save(update_fields=["status", "updated_at"])

    for line in sale.lines.select_for_update():
        if not line.item or not line.item.track_stock or line.reserved_quantity <= 0:
            continue
        stock = _stock_record_for_update(item=line.item, branch=sale.branch)
        release_qty = min(line.reserved_quantity, stock.reserved_quantity)
        stock.reserved_quantity = max(stock.reserved_quantity - release_qty, Decimal("0.00"))
        stock.save(update_fields=["reserved_quantity", "updated_at"])
        line.reserved_quantity = max(line.reserved_quantity - release_qty, Decimal("0.00"))
        line.save(update_fields=["reserved_quantity", "updated_at"])
        StockMovement.objects.create(
            item=line.item,
            branch=sale.branch,
            movement_type=StockMovement.MovementType.RELEASE,
            quantity=release_qty,
            previous_quantity=stock.quantity,
            new_quantity=stock.quantity,
            reference=sale.number,
            reason=note or "Liberación de reserva comercial",
            created_by=actor if getattr(actor, "is_authenticated", False) else None,
            confirmed_at=timezone.now(),
        )


@transaction.atomic
def confirm_sale(*, actor, sale: SaleRecord, note: str = "") -> SaleRecord:
    """ES: Ejecuta la operación «confirm sale» dentro del dominio de ventas. Además, conserva atomicidad y bloqueos explícitos, aplica autorización en backend, registra efectos auditables, rechaza estados o entradas inválidas.

    EN: Executes the «confirm sale» operation within the sales domain. It also preserves atomicity and explicit locking, enforces server-side authorization, records auditable effects, rejects invalid input or state.
    """

    sale = _locked_sale(sale)
    if actor is not None and not actor.has_perm_code("sales.sell", branch=sale.branch):
        raise ValidationError("No tienes permiso para vender en esta sucursal.")
    if not sale.can_be_confirmed:
        raise ValidationError("Esta operación no puede confirmarse como venta desde su estado actual.")
    if sale.vehicle:
        vehicle = Vehicle.objects.select_for_update().get(pk=sale.vehicle_id)
        conflict = _vehicle_conflict(sale=sale, vehicle=vehicle)
        if conflict:
            raise ValidationError(f"La unidad ya está comprometida por la operación {conflict.number}.")
        if sale.status == SaleRecord.Status.RESERVED and vehicle.status != Vehicle.Status.RESERVED:
            raise ValidationError("La unidad ya no conserva el estado de reserva esperado.")
        if sale.status != SaleRecord.Status.RESERVED and vehicle.status != Vehicle.Status.AVAILABLE:
            raise ValidationError("El vehículo no está disponible para venta.")
        vehicle.status = Vehicle.Status.SOLD
        vehicle.save(update_fields=["status", "updated_at"])

    for line in sale.lines.select_for_update():
        if not line.item or not line.item.track_stock:
            line.fulfilled_quantity = line.quantity
            line.save(update_fields=["fulfilled_quantity", "updated_at"])
            continue
        stock = _stock_record_for_update(item=line.item, branch=sale.branch)
        previous = stock.quantity
        own_reserved = min(line.reserved_quantity, stock.reserved_quantity)
        reserved_by_others = max(stock.reserved_quantity - own_reserved, Decimal("0.00"))
        if previous - reserved_by_others < line.quantity:
            raise ValidationError(f"Stock insuficiente para vender {line.item.sku} en {sale.branch.name}.")
        stock.quantity = previous - line.quantity
        stock.reserved_quantity = max(stock.reserved_quantity - own_reserved, Decimal("0.00"))
        line.reserved_quantity = max(line.reserved_quantity - own_reserved, Decimal("0.00"))
        stock.last_movement_at = timezone.now()
        stock.save(update_fields=["quantity", "reserved_quantity", "last_movement_at", "updated_at"])
        line.fulfilled_quantity = line.quantity
        line.save(update_fields=["fulfilled_quantity", "reserved_quantity", "updated_at"])
        StockMovement.objects.create(
            item=line.item,
            branch=sale.branch,
            movement_type=StockMovement.MovementType.SALE,
            quantity=line.quantity,
            previous_quantity=previous,
            new_quantity=stock.quantity,
            reference=sale.number,
            reason=note or "Venta comercial",
            created_by=actor if getattr(actor, "is_authenticated", False) else None,
            confirmed_at=timezone.now(),
        )

    previous = sale.status
    sale.kind = SaleRecord.Kind.SALE
    sale.status = SaleRecord.Status.SOLD
    sale.closed_at = timezone.now()
    sale.save(update_fields=["kind", "status", "closed_at", "updated_at"])
    recalculate_sale_totals(sale)
    create_status_history(sale=sale, previous=previous, new=sale.status, actor=actor, note=note)
    audit_log(user=actor, action="sales.confirm", target=sale, before={"status": previous}, after=_sale_snapshot(sale))
    _sync_origin_leads(actor=actor, sale=sale)
    return sale


@transaction.atomic
def cancel_sale(*, actor, sale: SaleRecord, note: str = "") -> SaleRecord:
    sale = _locked_sale(sale)
    if actor is not None and not (
        actor.has_perm_code("sales.quote", branch=sale.branch)
        or actor.has_perm_code("sales.reserve", branch=sale.branch)
    ):
        raise ValidationError("No tienes permiso para cancelar en esta sucursal.")
    if sale.status in {SaleRecord.Status.SOLD, SaleRecord.Status.VOID}:
        raise ValidationError("Una venta confirmada o anulada no se cancela desde este flujo.")
    if sale.payments.exclude(status=SalePayment.Status.VOID).exists():
        raise ValidationError("Anula los pagos pendientes o confirmados antes de cancelar la operación.")
    previous = sale.status
    if sale.status == SaleRecord.Status.RESERVED:
        release_sale_reservations(actor=actor, sale=sale, note=note or "Cancelación de operación")
    sale.status = SaleRecord.Status.CANCELLED
    sale.closed_at = timezone.now()
    sale.save(update_fields=["status", "closed_at", "updated_at"])
    create_status_history(sale=sale, previous=previous, new=sale.status, actor=actor, note=note)
    audit_log(user=actor, action="sales.cancel", target=sale, before={"status": previous}, after=_sale_snapshot(sale))
    _sync_origin_leads(actor=actor, sale=sale)
    return sale


@transaction.atomic
def expire_sale(*, actor, sale: SaleRecord, note: str = "") -> SaleRecord:
    sale = _locked_sale(sale)
    if actor is not None and not actor.has_perm_code("sales.reserve", branch=sale.branch):
        raise ValidationError("No tienes permiso para expirar en esta sucursal.")
    if sale.is_closed:
        raise ValidationError("La operación ya está cerrada.")
    if sale.payments.exclude(status=SalePayment.Status.VOID).exists():
        raise ValidationError("Anula los pagos pendientes o confirmados antes de expirar la operación.")
    previous = sale.status
    if sale.status == SaleRecord.Status.RESERVED:
        release_sale_reservations(actor=actor, sale=sale, note=note or "Expiración de reserva")
    sale.status = SaleRecord.Status.EXPIRED
    sale.closed_at = timezone.now()
    sale.save(update_fields=["status", "closed_at", "updated_at"])
    create_status_history(sale=sale, previous=previous, new=sale.status, actor=actor, note=note)
    audit_log(user=actor, action="sales.expire", target=sale, before={"status": previous}, after=_sale_snapshot(sale))
    _sync_origin_leads(actor=actor, sale=sale)
    return sale
