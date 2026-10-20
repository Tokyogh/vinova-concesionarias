"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de inventario.

EN: This module defines persistent models, states, and constraints for the inventory domain.

Contexto existente / Existing context:
Persistent domain models and database constraints for the inventory domain.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.common.models import SoftDeleteModel, TimeStampedModel
from apps.common.validators import validate_upload_extension, validate_upload_size


class InventoryCategory(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True, db_index=True)
    slug = models.SlugField(max_length=140, unique=True, db_index=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Categoría de inventario"
        verbose_name_plural = "Categorías de inventario"

    def __str__(self):
        return self.name


class InventoryItem(TimeStampedModel, SoftDeleteModel):
    """ES: Agrupa el componente «inventory item» del dominio de inventario y sus reglas relacionadas.

    EN: Groups the «inventory item» component and its related rules in the inventory domain.
    """

    class ItemType(models.TextChoices):
        OIL = "oil", "Aceite"
        FILTER = "filter", "Filtro"
        SPARE_PART = "spare_part", "Repuesto"
        ACCESSORY = "accessory", "Accesorio"
        SERVICE = "service", "Servicio"
        MAINTENANCE = "maintenance", "Mantenimiento"
        OTHER = "other", "Otro"

    class Status(models.TextChoices):
        ACTIVE = "active", "Activo"
        INACTIVE = "inactive", "Inactivo"
        ARCHIVED = "archived", "Archivado"

    category = models.ForeignKey(InventoryCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name="items")
    name = models.CharField(max_length=180, db_index=True)
    sku = models.CharField(max_length=60, unique=True, db_index=True)
    item_type = models.CharField(max_length=30, choices=ItemType.choices, default=ItemType.SPARE_PART, db_index=True)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=30, default="unidad", help_text="Ej.: unidad, litro, kit, hora.")
    price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    image = models.ImageField(upload_to="inventory/items/", blank=True, null=True, validators=[validate_upload_extension, validate_upload_size])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    is_public = models.BooleanField(default=False, db_index=True)
    track_stock = models.BooleanField(default=True, help_text="Desactivar para servicios que no manejan unidades físicas.")
    created_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="created_inventory_items")

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["sku"]),
            models.Index(fields=["status", "item_type"]),
            models.Index(fields=["category", "status"]),
            models.Index(fields=["created_at"]),
        ]
        verbose_name = "Artículo de inventario"
        verbose_name_plural = "Artículos de inventario"

    def __str__(self):
        return f"{self.sku} · {self.name}"

    @property
    def total_stock(self):
        if hasattr(self, "total_stock_amount"):
            return self.total_stock_amount or Decimal("0")
        prefetched = getattr(self, "_prefetched_objects_cache", {}).get("stock_records")
        if prefetched is not None:
            return sum((stock.quantity for stock in prefetched), Decimal("0"))
        return self.stock_records.aggregate(total=models.Sum("quantity"))["total"] or Decimal("0")

    @property
    def has_low_stock(self):
        if hasattr(self, "has_low_stock_scoped"):
            return self.has_low_stock_scoped
        prefetched = getattr(self, "_prefetched_objects_cache", {}).get("stock_records")
        if prefetched is not None:
            return any(stock.is_low_stock for stock in prefetched)
        return self.stock_records.filter(quantity__lte=models.F("minimum_stock"), minimum_stock__gt=0).exists()


# ES: El catálogo público se limita a bienes físicos; servicios y mantenimiento
# permanecen en los flujos internos hasta que exista una política comercial.
# EN: The public catalog is limited to physical goods; services and maintenance
# stay internal until a commercial publication policy exists.
PUBLIC_CATALOG_ITEM_TYPES = (
    InventoryItem.ItemType.OIL,
    InventoryItem.ItemType.FILTER,
    InventoryItem.ItemType.SPARE_PART,
    InventoryItem.ItemType.ACCESSORY,
    InventoryItem.ItemType.OTHER,
)


class BranchStock(TimeStampedModel):
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="stock_records")
    branch = models.ForeignKey("branches.Branch", on_delete=models.CASCADE, related_name="inventory_stock")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    reserved_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    minimum_stock = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    location_code = models.CharField(max_length=80, blank=True, help_text="Percha, bodega, zona o ubicación interna.")
    last_movement_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["item", "branch"], name="unique_stock_per_item_branch"),
            models.CheckConstraint(condition=Q(quantity__gte=0), name="stock_quantity_non_negative"),
            models.CheckConstraint(condition=Q(reserved_quantity__gte=0), name="stock_reserved_non_negative"),
            models.CheckConstraint(
                condition=Q(reserved_quantity__lte=models.F("quantity")),
                name="stock_reserved_lte_quantity",
            ),
            models.CheckConstraint(condition=Q(minimum_stock__gte=0), name="stock_minimum_non_negative"),
        ]
        indexes = [
            models.Index(fields=["branch", "item"]),
            models.Index(fields=["item", "quantity"]),
            models.Index(fields=["quantity", "minimum_stock"]),
        ]
        ordering = ["branch__name", "item__name"]
        verbose_name = "Stock por sucursal"
        verbose_name_plural = "Stock por sucursal"

    def __str__(self):
        return f"{self.item.sku} · {self.branch.name}: {self.quantity}"

    @property
    def available_quantity(self):
        return max(self.quantity - self.reserved_quantity, Decimal("0"))

    @property
    def is_low_stock(self):
        return self.minimum_stock > 0 and self.quantity <= self.minimum_stock

    def clean(self):
        if self.reserved_quantity > self.quantity:
            raise ValidationError({"reserved_quantity": "La cantidad reservada no puede superar el stock físico."})


class StockMovement(TimeStampedModel):
    class MovementType(models.TextChoices):
        IN = "in", "Entrada"
        OUT = "out", "Salida"
        ADJUST = "adjust", "Ajuste"
        TRANSFER = "transfer", "Transferencia"
        SALE = "sale", "Venta"
        RETURN = "return", "Devolución"
        RESERVE = "reserve", "Reserva"
        RELEASE = "release", "Liberación"

    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmado"
        VOID = "void", "Anulado"

    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name="movements")
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="stock_movements")
    destination_branch = models.ForeignKey("branches.Branch", null=True, blank=True, on_delete=models.PROTECT, related_name="incoming_stock_movements")
    movement_type = models.CharField(max_length=20, choices=MovementType.choices, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED, db_index=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    previous_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    new_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    destination_previous_quantity = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    destination_new_quantity = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    reference = models.CharField(max_length=140, blank=True, db_index=True, help_text="Factura, orden, guía, transferencia, ajuste o documento relacionado.")
    reason = models.TextField(blank=True)
    created_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="created_stock_movements")
    confirmed_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-confirmed_at", "-created_at"]
        indexes = [
            models.Index(fields=["item", "branch", "confirmed_at"]),
            models.Index(fields=["movement_type", "status"]),
            models.Index(fields=["reference"]),
            models.Index(fields=["created_at"]),
        ]
        verbose_name = "Movimiento de stock"
        verbose_name_plural = "Movimientos de stock"

    def __str__(self):
        return f"{self.get_movement_type_display()} · {self.item.sku} · {self.quantity}"

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError({"quantity": "La cantidad del movimiento debe ser mayor a cero."})
        if self.movement_type == self.MovementType.TRANSFER and not self.destination_branch:
            raise ValidationError({"destination_branch": "Una transferencia requiere sucursal destino."})
        if self.destination_branch and self.destination_branch_id == self.branch_id:
            raise ValidationError({"destination_branch": "La sucursal destino debe ser diferente a la sucursal origen."})
