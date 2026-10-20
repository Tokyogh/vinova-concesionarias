"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de postventa.

EN: This module defines persistent models, states, and constraints for the post sales domain.

Contexto existente / Existing context:
Persistent domain models and database constraints for the post sales domain.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class ServiceOrder(TimeStampedModel):
    """ES: Agrupa el componente «service order» del dominio de postventa y sus reglas relacionadas. Además, rechaza estados o entradas inválidas.

    EN: Groups the «service order» component and its related rules in the post sales domain. It also rejects invalid input or state.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Borrador"
        SCHEDULED = "scheduled", "Programada"
        IN_PROGRESS = "in_progress", "En proceso"
        COMPLETED = "completed", "Completada"
        CANCELLED = "cancelled", "Cancelada"

    number = models.CharField(max_length=30, unique=True, db_index=True)
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="service_orders")
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="service_orders")
    vehicle = models.ForeignKey("vehicles.Vehicle", on_delete=models.PROTECT, related_name="service_orders")
    responsible = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="responsible_service_orders",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    description = models.TextField()
    scheduled_at = models.DateTimeField(null=True, blank=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    reception_mileage = models.PositiveIntegerField(null=True, blank=True)
    delivery_mileage = models.PositiveIntegerField(null=True, blank=True)
    diagnosis = models.TextField(blank=True)
    cancellation_reason = models.CharField(max_length=220, blank=True)
    next_service_date = models.DateField(null=True, blank=True, db_index=True)
    next_service_mileage = models.PositiveIntegerField(null=True, blank=True)
    labor_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    parts_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    external_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    documents = models.ManyToManyField("documents.PrivateDocument", blank=True, related_name="service_orders")
    created_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_service_orders",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["vehicle", "created_at"]),
            models.Index(fields=["customer", "created_at"]),
            models.Index(fields=["responsible", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(labor_cost__gte=0, parts_cost__gte=0, external_cost__gte=0, total_cost__gte=0),
                name="service_order_costs_nonnegative",
            )
        ]

    def clean(self):
        if self.vehicle_id and self.branch_id and self.vehicle.branch_id != self.branch_id:
            raise ValidationError({"vehicle": "El vehículo pertenece a otra sucursal."})
        if self.customer_id and self.branch_id and self.customer.assigned_branch_id not in (None, self.branch_id):
            raise ValidationError({"customer": "El cliente pertenece a otra sucursal."})
        if (
            self.reception_mileage is not None
            and self.delivery_mileage is not None
            and self.delivery_mileage < self.reception_mileage
        ):
            raise ValidationError({"delivery_mileage": "El kilometraje de entrega no puede ser menor al de recepción."})
        baseline = self.delivery_mileage if self.delivery_mileage is not None else self.reception_mileage
        if self.next_service_mileage is not None and baseline is not None and self.next_service_mileage <= baseline:
            raise ValidationError({"next_service_mileage": "La próxima atención debe superar el kilometraje registrado."})

    def calculate_total(self):
        self.total_cost = sum((self.labor_cost, self.parts_cost, self.external_cost), Decimal("0.00"))
        return self.total_cost

    def __str__(self):
        return self.number


class ServiceOrderLine(TimeStampedModel):
    class LineType(models.TextChoices):
        SERVICE = "service", "Servicio"
        LABOR = "labor", "Mano de obra"
        PART = "part", "Repuesto"
        EXTERNAL = "external", "Servicio externo"

    order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name="lines")
    line_type = models.CharField(max_length=20, choices=LineType.choices, db_index=True)
    description = models.CharField(max_length=220)
    responsible = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name="service_line_quantity_positive"),
            models.CheckConstraint(condition=Q(unit_cost__gte=0, total_cost__gte=0), name="service_line_costs_nonnegative"),
        ]

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError({"quantity": "La cantidad debe ser mayor a cero."})
        if self.unit_cost < 0:
            raise ValidationError({"unit_cost": "El costo no puede ser negativo."})

    def calculate_total(self):
        self.total_cost = (self.quantity * self.unit_cost).quantize(Decimal("0.01"))
        return self.total_cost


class ServiceOrderHistory(TimeStampedModel):
    order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name="history")
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, choices=ServiceOrder.Status.choices, db_index=True)
    changed_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL)
    note = models.CharField(max_length=220, blank=True)
    snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["order", "created_at"])]
