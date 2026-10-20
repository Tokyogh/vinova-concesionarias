"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de facturación.

EN: This module defines persistent models, states, and constraints for the invoices domain.

Contexto existente / Existing context:
Persistent domain models and database constraints for the invoices domain.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.common.models import SoftDeleteModel, TimeStampedModel


class InvoiceSequence(TimeStampedModel):
    """Numeración configurable por sucursal.

    No reemplaza integración tributaria electrónica. Deja preparada la lógica de
    numeración interna para que una empresa luego conecte SRI/ERP externo si lo
    requiere.
    """

    branch = models.ForeignKey("branches.Branch", on_delete=models.CASCADE, related_name="invoice_sequences")
    prefix = models.CharField(max_length=20, default="FAC", db_index=True)
    next_number = models.PositiveIntegerField(default=1)
    padding = models.PositiveSmallIntegerField(default=6)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["branch", "prefix"], name="unique_invoice_sequence_per_branch_prefix")]
        indexes = [models.Index(fields=["branch", "is_active"])]
        ordering = ["branch__name", "prefix"]
        verbose_name = "Secuencia de factura"
        verbose_name_plural = "Secuencias de facturas"

    def __str__(self):
        return f"{self.branch} · {self.prefix}"

    def build_number(self):
        return f"{self.prefix}-{self.branch.code.upper()}-{self.next_number:0{self.padding}d}"


class InvoiceRecord(TimeStampedModel, SoftDeleteModel):
    """ES: Agrupa el componente «invoice record» del dominio de facturación y sus reglas relacionadas. Además, aplica autorización en backend, rechaza estados o entradas inválidas.

    EN: Groups the «invoice record» component and its related rules in the invoices domain. It also enforces server-side authorization, rejects invalid input or state.
    """

    class InvoiceType(models.TextChoices):
        PROFORMA = "proforma", "Proforma"
        INVOICE = "invoice", "Factura"
        RECEIPT = "receipt", "Comprobante interno"
        CREDIT_NOTE = "credit_note", "Nota de crédito"

    class Status(models.TextChoices):
        DRAFT = "draft", "Borrador"
        ISSUED = "issued", "Emitida"
        PARTIAL = "partial", "Pago parcial"
        PAID = "paid", "Pagada"
        VOID = "void", "Anulada"
        CANCELLED = "cancelled", "Cancelada"

    number = models.CharField(max_length=40, unique=True, db_index=True)
    invoice_type = models.CharField(max_length=20, choices=InvoiceType.choices, default=InvoiceType.INVOICE, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    sale = models.ForeignKey("sales.SaleRecord", null=True, blank=True, on_delete=models.PROTECT, related_name="invoices")
    company = models.ForeignKey("companies.Company", on_delete=models.PROTECT, related_name="invoices")
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="invoices")
    customer = models.ForeignKey("customers.Customer", null=True, blank=True, on_delete=models.SET_NULL, related_name="invoices")
    customer_name = models.CharField(max_length=180, db_index=True)
    customer_document = models.CharField(max_length=30, blank=True, db_index=True)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=40, blank=True)
    issue_date = models.DateField(default=timezone.localdate, db_index=True)
    due_date = models.DateField(null=True, blank=True, db_index=True)
    currency = models.CharField(max_length=10, default="USD")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    balance_due = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    authorization_number = models.CharField(max_length=80, blank=True, db_index=True)
    access_key = models.CharField(max_length=80, blank=True, db_index=True)
    external_reference = models.CharField(max_length=100, blank=True, db_index=True)
    notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    linked_document = models.ForeignKey("documents.PrivateDocument", null=True, blank=True, on_delete=models.SET_NULL, related_name="linked_invoices")
    created_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="created_invoices")
    issued_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="issued_invoices")
    issued_at = models.DateTimeField(null=True, blank=True, db_index=True)
    voided_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="voided_invoices")
    voided_at = models.DateTimeField(null=True, blank=True)
    void_reason = models.CharField(max_length=220, blank=True)

    class Meta:
        ordering = ["-issue_date", "-created_at"]
        indexes = [
            models.Index(fields=["status", "invoice_type"]),
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["customer", "issue_date"]),
            models.Index(fields=["sale", "status"]),
            models.Index(fields=["number"]),
            models.Index(fields=["issue_date"]),
        ]
        verbose_name = "Factura / comprobante"
        verbose_name_plural = "Facturas / comprobantes"

    def __str__(self):
        return f"{self.number} · {self.customer_name}"

    @property
    def can_be_issued(self):
        return self.status == self.Status.DRAFT and self.lines.exists()

    @property
    def can_be_voided(self):
        return self.status in {self.Status.DRAFT, self.Status.ISSUED, self.Status.PARTIAL}

    @property
    def is_closed(self):
        return self.status in {self.Status.PAID, self.Status.VOID, self.Status.CANCELLED}

    def clean(self):
        if self.due_date and self.due_date < self.issue_date:
            raise ValidationError({"due_date": "El vencimiento no puede ser anterior a la fecha de emisión."})
        if self.total < 0:
            raise ValidationError({"total": "El total no puede ser negativo."})


class InvoiceLine(TimeStampedModel):
    invoice = models.ForeignKey(InvoiceRecord, on_delete=models.CASCADE, related_name="lines")
    description = models.CharField(max_length=220)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("1.00"))
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("15.00"))
    line_subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    line_tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    source_sale_line = models.ForeignKey("sales.SaleLine", null=True, blank=True, on_delete=models.SET_NULL, related_name="invoice_lines")

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["invoice"]), models.Index(fields=["source_sale_line"])]
        verbose_name = "Línea de factura"
        verbose_name_plural = "Líneas de factura"

    def __str__(self):
        return f"{self.invoice.number} · {self.description}"

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError({"quantity": "La cantidad debe ser mayor a cero."})
        if self.unit_price < 0 or self.discount_amount < 0 or self.tax_rate < 0:
            raise ValidationError("Precio, descuento e impuesto no pueden ser negativos.")
        if self.discount_amount > (self.quantity * self.unit_price):
            raise ValidationError({"discount_amount": "El descuento no puede superar el subtotal."})

    def calculate_totals(self):
        subtotal = (Decimal(str(self.quantity or 0)) * Decimal(str(self.unit_price or 0))).quantize(Decimal("0.01"))
        net = max(subtotal - Decimal(str(self.discount_amount or 0)), Decimal("0.00")).quantize(Decimal("0.01"))
        tax = (net * (Decimal(str(self.tax_rate or 0)) / Decimal("100"))).quantize(Decimal("0.01"))
        self.line_subtotal = subtotal
        self.line_tax = tax
        self.line_total = (net + tax).quantize(Decimal("0.01"))
        return self


class InvoicePaymentApplication(TimeStampedModel):
    invoice = models.ForeignKey(InvoiceRecord, on_delete=models.CASCADE, related_name="payment_applications")
    sale_payment = models.ForeignKey("sales.SalePayment", null=True, blank=True, on_delete=models.SET_NULL, related_name="invoice_applications")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    applied_at = models.DateTimeField(default=timezone.now, db_index=True)
    notes = models.CharField(max_length=220, blank=True)
    applied_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="applied_invoice_payments")

    class Meta:
        ordering = ["-applied_at"]
        indexes = [models.Index(fields=["invoice", "applied_at"]), models.Index(fields=["sale_payment"])]
        verbose_name = "Aplicación de pago"
        verbose_name_plural = "Aplicaciones de pagos"

    def clean(self):
        if self.amount <= 0:
            raise ValidationError({"amount": "El valor aplicado debe ser mayor a cero."})


class InvoiceStatusHistory(TimeStampedModel):
    invoice = models.ForeignKey(InvoiceRecord, on_delete=models.CASCADE, related_name="status_history")
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, choices=InvoiceRecord.Status.choices, db_index=True)
    changed_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="invoice_status_changes")
    note = models.CharField(max_length=220, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["invoice", "created_at"]), models.Index(fields=["new_status"])]
        verbose_name = "Historial de factura"
        verbose_name_plural = "Historial de facturas"
