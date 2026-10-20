"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de ventas.

EN: This module defines persistent models, states, and constraints for the sales domain.

Contexto existente / Existing context:
Persistent domain models and database constraints for the sales domain.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import SoftDeleteModel, TimeStampedModel


class SaleRecord(TimeStampedModel, SoftDeleteModel):
    """Operación comercial: cotización, reserva o venta.

    Se diseñó como documento comercial único para evitar duplicar flujos. Una
    operación puede iniciar como cotización, pasar a reserva y terminar como
    venta confirmada. Facturación/documentos privados se conectarán más adelante.
    """

    class Kind(models.TextChoices):
        QUOTE = "quote", "Cotización"
        RESERVATION = "reservation", "Reserva"
        SALE = "sale", "Venta"

    class Status(models.TextChoices):
        DRAFT = "draft", "Borrador"
        QUOTED = "quoted", "Cotizado"
        RESERVED = "reserved", "Reservado"
        APPROVED = "approved", "Aprobado"
        SOLD = "sold", "Vendido"
        CANCELLED = "cancelled", "Cancelado"
        VOID = "void", "Anulado"
        EXPIRED = "expired", "Expirado"

    class Source(models.TextChoices):
        WEB = "web", "Web"
        SHOWROOM = "showroom", "Sala de ventas"
        PHONE = "phone", "Teléfono"
        WHATSAPP = "whatsapp", "WhatsApp"
        REFERRAL = "referral", "Referido"
        FAIR = "fair", "Feria / evento"
        OTHER = "other", "Otro"

    number = models.CharField(max_length=30, unique=True, db_index=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.QUOTE, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="sales")
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="sales")
    advisor = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="advised_sales")
    vehicle = models.ForeignKey("vehicles.Vehicle", null=True, blank=True, on_delete=models.PROTECT, related_name="sales")
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.SHOWROOM, db_index=True)
    vehicle_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    vehicle_discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    line_subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("15.00"), help_text="Porcentaje de IVA aplicado al documento.")
    tax_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    balance_due = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    valid_until = models.DateField(null=True, blank=True, db_index=True)
    reserved_until = models.DateTimeField(null=True, blank=True, db_index=True)
    closed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    created_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="created_sales")

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["vehicle"],
                condition=Q(vehicle__isnull=False, is_deleted=False, status__in=["reserved", "sold"]),
                name="unique_active_vehicle_commitment",
            ),
            models.CheckConstraint(
                condition=~Q(status="reserved") | Q(reserved_until__isnull=False),
                name="reserved_sale_requires_expiry",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "kind"]),
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["customer", "created_at"]),
            models.Index(fields=["vehicle", "status"]),
            models.Index(fields=["number"]),
            models.Index(fields=["created_at"]),
        ]
        verbose_name = "Operación comercial"
        verbose_name_plural = "Operaciones comerciales"

    def __str__(self):
        return f"{self.number} · {self.customer.display_name}"

    @property
    def can_be_reserved(self):
        return self.status in {self.Status.DRAFT, self.Status.QUOTED, self.Status.APPROVED}

    @property
    def can_be_confirmed(self):
        return self.status in {self.Status.QUOTED, self.Status.RESERVED, self.Status.APPROVED}

    @property
    def is_closed(self):
        return self.status in {self.Status.SOLD, self.Status.CANCELLED, self.Status.VOID, self.Status.EXPIRED}

    def clean(self):
        if self.vehicle_discount < 0:
            raise ValidationError({"vehicle_discount": "El descuento del vehículo no puede ser negativo."})
        if self.vehicle_price < 0:
            raise ValidationError({"vehicle_price": "El precio del vehículo no puede ser negativo."})
        if self.vehicle and self.vehicle.branch_id and self.branch_id and self.vehicle.branch_id != self.branch_id:
            raise ValidationError({"vehicle": "El vehículo pertenece a otra sucursal."})
        if self.tax_rate < 0:
            raise ValidationError({"tax_rate": "El impuesto no puede ser negativo."})
        if self.status == self.Status.RESERVED and not self.reserved_until:
            raise ValidationError({"reserved_until": "Toda reserva debe tener una fecha de vencimiento."})
        if self.status == self.Status.RESERVED and self.reserved_until and self.reserved_until <= timezone.now():
            raise ValidationError({"reserved_until": "La reserva debe vencer en una fecha futura."})


class SaleLine(TimeStampedModel):
    sale = models.ForeignKey(SaleRecord, on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey("inventory.InventoryItem", null=True, blank=True, on_delete=models.PROTECT, related_name="sale_lines")
    description = models.CharField(max_length=220)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("1.00"))
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    line_subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    reserved_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    fulfilled_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    notes = models.CharField(max_length=220, blank=True)

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["sale", "item"]), models.Index(fields=["item"])]
        verbose_name = "Línea comercial"
        verbose_name_plural = "Líneas comerciales"

    def __str__(self):
        return f"{self.sale.number} · {self.description}"

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError({"quantity": "La cantidad debe ser mayor a cero."})
        if self.unit_price < 0:
            raise ValidationError({"unit_price": "El precio unitario no puede ser negativo."})
        if self.discount_amount < 0:
            raise ValidationError({"discount_amount": "El descuento no puede ser negativo."})
        subtotal = self.quantity * self.unit_price
        if self.discount_amount > subtotal:
            raise ValidationError({"discount_amount": "El descuento no puede superar el subtotal de la línea."})

    def calculate_totals(self):
        quantity = Decimal(str(self.quantity or 0))
        unit_price = Decimal(str(self.unit_price or 0))
        discount = Decimal(str(self.discount_amount or 0))
        self.line_subtotal = (quantity * unit_price).quantize(Decimal("0.01"))
        self.line_total = max(self.line_subtotal - discount, Decimal("0.00")).quantize(Decimal("0.01"))
        return self


class SalePayment(TimeStampedModel):
    class Method(models.TextChoices):
        CASH = "cash", "Efectivo"
        TRANSFER = "transfer", "Transferencia"
        CARD = "card", "Tarjeta"
        CREDIT = "credit", "Crédito directo"
        FINANCING = "financing", "Financiamiento"
        CHECK = "check", "Cheque"
        OTHER = "other", "Otro"

    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        CONFIRMED = "confirmed", "Confirmado"
        VOID = "void", "Anulado"

    sale = models.ForeignKey(SaleRecord, on_delete=models.CASCADE, related_name="payments")
    method = models.CharField(max_length=20, choices=Method.choices, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=140, blank=True, db_index=True)
    paid_at = models.DateTimeField(default=timezone.now, db_index=True)
    received_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="received_sale_payments")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-paid_at", "-created_at"]
        indexes = [models.Index(fields=["sale", "status"]), models.Index(fields=["reference"])]
        verbose_name = "Pago comercial"
        verbose_name_plural = "Pagos comerciales"

    def __str__(self):
        return f"{self.sale.number} · {self.amount}"

    def clean(self):
        if self.amount <= 0:
            raise ValidationError({"amount": "El pago debe ser mayor a cero."})


class SaleStatusHistory(TimeStampedModel):
    sale = models.ForeignKey(SaleRecord, on_delete=models.CASCADE, related_name="status_history")
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, choices=SaleRecord.Status.choices, db_index=True)
    changed_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="sale_status_changes")
    note = models.CharField(max_length=220, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["sale", "created_at"]), models.Index(fields=["new_status"])]
        verbose_name = "Historial de estado comercial"
        verbose_name_plural = "Historial de estados comerciales"

    def __str__(self):
        return f"{self.sale.number}: {self.previous_status} → {self.new_status}"
