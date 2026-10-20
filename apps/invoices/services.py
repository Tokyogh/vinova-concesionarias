"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de facturación.

EN: This module implements business services and transactional effects for the invoices domain.

Contexto existente / Existing context:
Transactional business services for the invoices domain.
"""

from __future__ import annotations

import hashlib
import logging
import re
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.scopes import accessible_branch_ids
from apps.audit.services import audit_log
from apps.documents.models import PrivateDocument
from apps.invoices.pdf import render_invoice_pdf
from apps.invoices.selectors import INVOICE_ISSUE_PERMISSIONS, INVOICE_SCOPE_PERMISSIONS, INVOICE_VOID_PERMISSIONS
from apps.invoices.models import (
    InvoiceLine,
    InvoicePaymentApplication,
    InvoiceRecord,
    InvoiceSequence,
    InvoiceStatusHistory,
)
from apps.sales.models import SalePayment, SaleRecord

logger = logging.getLogger(__name__)


def _delete_generated_pdf(storage, name: str) -> None:
    if not name:
        return
    try:
        storage.delete(name)
    except Exception as exc:  # noqa: BLE001 - cleanup must not mask the original failure
        logger.warning("No se pudo limpiar un PDF de factura incompleto (%s).", exc.__class__.__name__)


def _money(value) -> Decimal:
    return Decimal(value or 0).quantize(Decimal("0.01"))


def _require_invoice_branch_access(*, actor, branch, permission_codes) -> None:
    if actor is None or not getattr(actor, "is_authenticated", False):
        raise ValidationError("Debes autenticarte para operar facturas.")
    branch_ids = accessible_branch_ids(actor, permission_codes=permission_codes)
    if branch_ids is not None and (branch is None or branch.pk not in branch_ids):
        raise ValidationError("No tienes permiso para operar facturas en esta sucursal.")


def _invoice_snapshot(invoice: InvoiceRecord) -> dict:
    return {
        "number": invoice.number,
        "invoice_type": invoice.invoice_type,
        "status": invoice.status,
        "sale_id": invoice.sale_id,
        "customer_name": invoice.customer_name,
        "branch_id": invoice.branch_id,
        "total": str(invoice.total),
        "amount_paid": str(invoice.amount_paid),
        "balance_due": str(invoice.balance_due),
    }


def _customer_snapshot(customer):
    if not customer:
        return {"name": "Consumidor final", "document": "", "email": "", "phone": ""}
    return {
        "name": customer.display_name,
        "document": customer.identification_number or "",
        "email": customer.email or "",
        "phone": customer.phone or customer.whatsapp or "",
    }


def create_status_history(*, invoice: InvoiceRecord, previous="", new: str, actor=None, note="", metadata=None):
    return InvoiceStatusHistory.objects.create(
        invoice=invoice,
        previous_status=previous or "",
        new_status=new,
        changed_by=actor if getattr(actor, "is_authenticated", False) else None,
        note=note,
        metadata=metadata or {},
    )


@transaction.atomic
def next_invoice_number(*, branch, invoice_type=InvoiceRecord.InvoiceType.INVOICE) -> str:
    prefix = {
        InvoiceRecord.InvoiceType.PROFORMA: "PRO",
        InvoiceRecord.InvoiceType.INVOICE: "FAC",
        InvoiceRecord.InvoiceType.RECEIPT: "REC",
        InvoiceRecord.InvoiceType.CREDIT_NOTE: "NC",
    }.get(invoice_type, "FAC")
    sequence, _ = InvoiceSequence.objects.select_for_update().get_or_create(
        branch=branch, prefix=prefix, defaults={"next_number": 1, "padding": 6}
    )
    number = sequence.build_number()
    sequence.next_number += 1
    sequence.save(update_fields=["next_number", "updated_at"])
    while InvoiceRecord.objects.filter(number=number).exists():
        number = sequence.build_number()
        sequence.next_number += 1
        sequence.save(update_fields=["next_number", "updated_at"])
    return number


@transaction.atomic
def recalculate_invoice_totals(invoice: InvoiceRecord) -> InvoiceRecord:
    """ES: Ejecuta la operación «recalculate invoice totals» dentro del dominio de facturación.

    EN: Executes the «recalculate invoice totals» operation within the invoices domain.
    """

    for line in invoice.lines.all():
        line.calculate_totals()
        line.save(update_fields=["line_subtotal", "line_tax", "line_total", "updated_at"])
    line_subtotal = invoice.lines.aggregate(total=Sum("line_subtotal"))["total"] or Decimal("0.00")
    line_tax = invoice.lines.aggregate(total=Sum("line_tax"))["total"] or Decimal("0.00")
    line_total = invoice.lines.aggregate(total=Sum("line_total"))["total"] or Decimal("0.00")
    discount_total = sum((_money(line.discount_amount) for line in invoice.lines.all()), Decimal("0.00"))
    invoice.subtotal = _money(line_subtotal - discount_total)
    invoice.discount_total = _money(discount_total)
    invoice.tax_total = _money(line_tax)
    invoice.total = _money(line_total)
    invoice.amount_paid = _money(
        invoice.payment_applications.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    )
    invoice.balance_due = max(_money(invoice.total) - _money(invoice.amount_paid), Decimal("0.00"))
    if invoice.status in {InvoiceRecord.Status.ISSUED, InvoiceRecord.Status.PARTIAL, InvoiceRecord.Status.PAID}:
        if invoice.balance_due == 0 and invoice.total > 0:
            invoice.status = InvoiceRecord.Status.PAID
        elif invoice.amount_paid > 0:
            invoice.status = InvoiceRecord.Status.PARTIAL
        else:
            invoice.status = InvoiceRecord.Status.ISSUED
    invoice.save(
        update_fields=[
            "subtotal",
            "discount_total",
            "tax_total",
            "total",
            "amount_paid",
            "balance_due",
            "status",
            "updated_at",
        ]
    )
    return invoice


@transaction.atomic
def create_invoice_from_sale(
    *, actor, sale: SaleRecord, invoice_type: str, issue_date, due_date=None, notes="", internal_notes=""
) -> InvoiceRecord:
    _require_invoice_branch_access(actor=actor, branch=sale.branch, permission_codes=INVOICE_ISSUE_PERMISSIONS)
    if sale.status not in {SaleRecord.Status.SOLD, SaleRecord.Status.APPROVED, SaleRecord.Status.RESERVED}:
        raise ValidationError("Solo se puede facturar una operación aprobada, reservada o vendida.")
    company = sale.branch.company
    customer_data = _customer_snapshot(sale.customer)
    invoice = InvoiceRecord.objects.create(
        number=next_invoice_number(branch=sale.branch, invoice_type=invoice_type),
        invoice_type=invoice_type,
        status=InvoiceRecord.Status.DRAFT,
        sale=sale,
        company=company,
        branch=sale.branch,
        customer=sale.customer,
        customer_name=customer_data["name"],
        customer_document=customer_data["document"],
        customer_email=customer_data["email"],
        customer_phone=customer_data["phone"],
        issue_date=issue_date or timezone.localdate(),
        due_date=due_date,
        notes=notes,
        internal_notes=internal_notes,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    if sale.vehicle:
        InvoiceLine.objects.create(
            invoice=invoice,
            description=f"Vehículo {sale.vehicle.brand.name} {sale.vehicle.model.name} {sale.vehicle.year} · Código {sale.vehicle.internal_code}"
            + (f" · VIN {sale.vehicle.vin}" if sale.vehicle.vin else ""),
            quantity=Decimal("1.00"),
            unit_price=sale.vehicle_price,
            discount_amount=sale.vehicle_discount,
            tax_rate=sale.tax_rate,
        )
    for sale_line in sale.lines.select_related("item"):
        InvoiceLine.objects.create(
            invoice=invoice,
            description=sale_line.description,
            quantity=sale_line.quantity,
            unit_price=sale_line.unit_price,
            discount_amount=sale_line.discount_amount,
            tax_rate=sale.tax_rate,
            source_sale_line=sale_line,
        )
    create_status_history(
        invoice=invoice, new=invoice.status, actor=actor, note="Factura creada desde operación comercial"
    )
    recalculate_invoice_totals(invoice)
    audit_log(user=actor, action="invoices.create_from_sale", target=invoice, after=_invoice_snapshot(invoice))
    return invoice


@transaction.atomic
def add_invoice_line(*, actor, invoice: InvoiceRecord, form) -> InvoiceLine:
    _require_invoice_branch_access(actor=actor, branch=invoice.branch, permission_codes=INVOICE_ISSUE_PERMISSIONS)
    if invoice.status != InvoiceRecord.Status.DRAFT:
        raise ValidationError("Solo se pueden agregar líneas a facturas en borrador.")
    line = form.save(commit=False)
    line.invoice = invoice
    line.calculate_totals()
    line.full_clean()
    line.save()
    recalculate_invoice_totals(invoice)
    audit_log(
        user=actor,
        action="invoices.line_add",
        target=invoice,
        after={"description": line.description, "line_total": str(line.line_total)},
    )
    return line


@transaction.atomic
def issue_invoice(*, actor, invoice: InvoiceRecord, note="") -> InvoiceRecord:
    _require_invoice_branch_access(actor=actor, branch=invoice.branch, permission_codes=INVOICE_ISSUE_PERMISSIONS)
    if not invoice.can_be_issued:
        raise ValidationError("La factura debe estar en borrador y tener al menos una línea.")
    before = _invoice_snapshot(invoice)
    previous = invoice.status
    invoice.status = InvoiceRecord.Status.ISSUED
    invoice.issued_by = actor if getattr(actor, "is_authenticated", False) else None
    invoice.issued_at = timezone.now()
    invoice.full_clean()
    invoice.save(update_fields=["status", "issued_by", "issued_at", "updated_at"])
    create_status_history(
        invoice=invoice, previous=previous, new=invoice.status, actor=actor, note=note or "Factura emitida"
    )
    audit_log(user=actor, action="invoices.issue", target=invoice, before=before, after=_invoice_snapshot(invoice))
    apply_confirmed_sale_payments(actor=actor, invoice=invoice, note="Aplicación automática al emitir")
    document = ensure_invoice_pdf(actor=actor, invoice=invoice)
    if invoice.customer_id:
        from apps.notifications.services import schedule_customer_event_notification

        schedule_customer_event_notification(
            customer=invoice.customer,
            title=f"Factura {invoice.number} emitida",
            body=f"Tu comprobante {invoice.number} por {invoice.total} ya está disponible para consulta y descarga.",
            message_type="invoice",
            dedup_key=f"invoice:{invoice.pk}:issued",
            actor=actor,
            branch=invoice.branch,
            related_sale=invoice.sale,
            related_document=document,
        )
    return invoice


@transaction.atomic
def ensure_invoice_pdf(*, actor, invoice: InvoiceRecord, customer=None) -> PrivateDocument:
    """Create the single private PDF artifact for an invoice and reuse it thereafter."""
    InvoiceRecord.objects.select_for_update().only("pk").get(pk=invoice.pk)
    locked = (
        InvoiceRecord.objects.select_related(
            "company", "branch", "customer", "sale", "sale__vehicle", "linked_document"
        )
        .prefetch_related("lines")
        .get(pk=invoice.pk)
    )
    if customer is None:
        _require_invoice_branch_access(
            actor=actor,
            branch=locked.branch,
            permission_codes=INVOICE_SCOPE_PERMISSIONS,
        )
    elif (
        locked.customer_id != customer.pk
        or customer.account_id != getattr(actor, "pk", None)
        or not actor.has_perm_code("portal.access")
    ):
        raise ValidationError("No tienes permiso para generar este comprobante.")
    if locked.status == InvoiceRecord.Status.DRAFT:
        raise ValidationError("No se puede generar el PDF de un comprobante en borrador.")
    if locked.linked_document_id:
        return locked.linked_document

    payload = render_invoice_pdf(locked)
    digest = hashlib.sha256(payload).hexdigest()
    safe_number = re.sub(r"[^A-Za-z0-9_-]+", "-", locked.number).strip("-") or str(locked.pk)
    filename = f"factura-{safe_number}.pdf"
    document = PrivateDocument(
        title=f"Comprobante {locked.number}",
        document_type=PrivateDocument.DocumentType.INVOICE,
        status=PrivateDocument.Status.ACTIVE,
        branch=locked.branch,
        customer=locked.customer,
        vehicle=locked.sale.vehicle if locked.sale_id else None,
        sale=locked.sale,
        notes=f"Artefacto PDF emitido para {locked.number}.",
        is_confidential=True,
        file_hash=digest,
        original_name=filename,
        mime_type="application/pdf",
        size_bytes=len(payload),
        extension=".pdf",
        uploaded_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    try:
        document.file.save(filename, ContentFile(payload), save=False)
        document.save()
        locked.linked_document = document
        locked.save(update_fields=["linked_document", "updated_at"])
        audit_log(
            user=actor,
            action="invoices.pdf.create",
            target=locked,
            customer=locked.customer,
            metadata={"document_id": document.pk, "file_hash": digest, "size_bytes": len(payload)},
        )
    except Exception:
        _delete_generated_pdf(document.file.storage, document.file.name)
        invoice.linked_document = None
        raise
    invoice.linked_document = document
    return document


@transaction.atomic
def apply_payment(*, actor, invoice: InvoiceRecord, amount, sale_payment=None, notes=""):
    _require_invoice_branch_access(actor=actor, branch=invoice.branch, permission_codes=INVOICE_ISSUE_PERMISSIONS)
    if invoice.status in {InvoiceRecord.Status.DRAFT, InvoiceRecord.Status.VOID, InvoiceRecord.Status.CANCELLED}:
        raise ValidationError("Solo se pueden aplicar pagos a facturas emitidas, parciales o pagadas.")
    amount = _money(amount)
    if amount <= 0:
        raise ValidationError("El monto aplicado debe ser mayor a cero.")
    if amount > invoice.balance_due:
        raise ValidationError("El monto aplicado supera el saldo pendiente.")
    app = InvoicePaymentApplication.objects.create(
        invoice=invoice,
        sale_payment=sale_payment,
        amount=amount,
        notes=notes,
        applied_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    previous = invoice.status
    recalculate_invoice_totals(invoice)
    if invoice.status != previous:
        create_status_history(
            invoice=invoice, previous=previous, new=invoice.status, actor=actor, note="Estado actualizado por pago"
        )
    audit_log(
        user=actor,
        action="invoices.payment_apply",
        target=invoice,
        after={"amount": str(amount), "balance_due": str(invoice.balance_due)},
    )
    return app


@transaction.atomic
def apply_confirmed_sale_payments(*, actor, invoice: InvoiceRecord, note=""):
    _require_invoice_branch_access(actor=actor, branch=invoice.branch, permission_codes=INVOICE_ISSUE_PERMISSIONS)
    if not invoice.sale_id:
        return []
    created = []
    applied_payment_ids = set(
        invoice.payment_applications.exclude(sale_payment__isnull=True).values_list("sale_payment_id", flat=True)
    )
    for payment in invoice.sale.payments.filter(status=SalePayment.Status.CONFIRMED).exclude(
        id__in=applied_payment_ids
    ):
        invoice.refresh_from_db()
        if invoice.balance_due <= 0:
            break
        amount = min(_money(payment.amount), _money(invoice.balance_due))
        created.append(
            apply_payment(
                actor=actor,
                invoice=invoice,
                amount=amount,
                sale_payment=payment,
                notes=note or "Pago comercial confirmado",
            )
        )
    return created


@transaction.atomic
def void_invoice(*, actor, invoice: InvoiceRecord, reason: str) -> InvoiceRecord:
    _require_invoice_branch_access(actor=actor, branch=invoice.branch, permission_codes=INVOICE_VOID_PERMISSIONS)
    if not invoice.can_be_voided:
        raise ValidationError("Esta factura ya no puede anularse desde su estado actual.")
    if not reason.strip():
        raise ValidationError("Debes indicar el motivo de anulación.")
    before = _invoice_snapshot(invoice)
    previous = invoice.status
    invoice.status = InvoiceRecord.Status.VOID
    invoice.voided_by = actor if getattr(actor, "is_authenticated", False) else None
    invoice.voided_at = timezone.now()
    invoice.void_reason = reason.strip()[:220]
    invoice.save(update_fields=["status", "voided_by", "voided_at", "void_reason", "updated_at"])
    create_status_history(invoice=invoice, previous=previous, new=invoice.status, actor=actor, note=invoice.void_reason)
    audit_log(user=actor, action="invoices.void", target=invoice, before=before, after=_invoice_snapshot(invoice))
    if invoice.customer_id:
        from apps.notifications.services import schedule_customer_event_notification

        schedule_customer_event_notification(
            customer=invoice.customer,
            title=f"Factura {invoice.number} anulada",
            body=f"Tu comprobante {invoice.number} fue anulado. Motivo: {invoice.void_reason}",
            message_type="invoice",
            dedup_key=f"invoice:{invoice.pk}:void",
            actor=actor,
            branch=invoice.branch,
            related_sale=invoice.sale,
            related_document=invoice.linked_document,
        )
    return invoice
