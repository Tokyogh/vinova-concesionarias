"""ES: Implementa el comando administrativo «seed demo inventory» para inventario.

EN: Implements the «seed demo inventory» management command for inventory.

Contexto existente / Existing context:
Django management command for seed demo inventory.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.branches.models import Branch
from apps.inventory.models import InventoryCategory, InventoryItem, StockMovement
from apps.inventory.services import record_stock_movement


DEMO_CATEGORIES = [
    ("Aceites y lubricantes", "Productos para motor, transmisión y mantenimiento preventivo."),
    ("Filtros", "Filtros de aceite, aire, combustible y cabina."),
    ("Repuestos", "Partes mecánicas y eléctricas para operación de taller."),
    ("Accesorios", "Accesorios comerciales y extras instalables."),
    ("Servicios", "Servicios de taller y mantenimiento que no manejan stock físico."),
]

DEMO_ITEMS = [
    {"sku": "OIL-5W30-001", "name": "Aceite sintético 5W-30", "item_type": InventoryItem.ItemType.OIL, "category": "Aceites y lubricantes", "unit": "litro", "price": Decimal("12.50"), "cost": Decimal("8.40"), "stock": Decimal("48"), "minimum": Decimal("20")},
    {"sku": "FIL-AIR-002", "name": "Filtro de aire pickup", "item_type": InventoryItem.ItemType.FILTER, "category": "Filtros", "unit": "unidad", "price": Decimal("18.00"), "cost": Decimal("10.00"), "stock": Decimal("12"), "minimum": Decimal("10")},
    {"sku": "FIL-OIL-003", "name": "Filtro de aceite estándar", "item_type": InventoryItem.ItemType.FILTER, "category": "Filtros", "unit": "unidad", "price": Decimal("9.50"), "cost": Decimal("5.20"), "stock": Decimal("8"), "minimum": Decimal("15")},
    {"sku": "ACC-MAT-004", "name": "Kit de alfombras premium", "item_type": InventoryItem.ItemType.ACCESSORY, "category": "Accesorios", "unit": "kit", "price": Decimal("85.00"), "cost": Decimal("42.00"), "stock": Decimal("16"), "minimum": Decimal("6")},
    {"sku": "SRV-MNT-005", "name": "Mantenimiento preventivo 10.000 km", "item_type": InventoryItem.ItemType.SERVICE, "category": "Servicios", "unit": "servicio", "price": Decimal("95.00"), "cost": None, "stock": Decimal("0"), "minimum": Decimal("0"), "track_stock": False},
]


class Command(BaseCommand):
    help = "Crea datos demo de inventario, categorías, artículos y stock por sucursal."

    @transaction.atomic
    def handle(self, *args, **options):
        categories = {}
        for name, description in DEMO_CATEGORIES:
            category, _ = InventoryCategory.objects.update_or_create(slug=slugify(name), defaults={"name": name, "description": description, "is_active": True})
            categories[name] = category

        branches = list(Branch.objects.filter(is_active=True).order_by("id")[:2])
        if not branches:
            self.stdout.write(self.style.WARNING("No hay sucursales activas. Ejecuta primero seed_demo_organization."))
            return

        for data in DEMO_ITEMS:
            item, created = InventoryItem.objects.update_or_create(
                sku=data["sku"],
                defaults={
                    "name": data["name"],
                    "item_type": data["item_type"],
                    "category": categories[data["category"]],
                    "unit": data["unit"],
                    "price": data["price"],
                    "cost": data["cost"],
                    "status": InventoryItem.Status.ACTIVE,
                    "track_stock": data.get("track_stock", True),
                    "description": f"Demo Vinova Pro: {data['name']}.",
                },
            )
            if item.track_stock and created:
                record_stock_movement(actor=None, item=item, branch=branches[0], movement_type=StockMovement.MovementType.IN, quantity=data["stock"], reference="DEMO-INVENTORY", reason="Carga inicial demo")
                stock = item.stock_records.get(branch=branches[0])
                stock.minimum_stock = data["minimum"]
                stock.location_code = "Bodega A-01"
                stock.save(update_fields=["minimum_stock", "location_code", "updated_at"])
                if len(branches) > 1:
                    extra = max(data["stock"] / Decimal("4"), Decimal("1"))
                    record_stock_movement(actor=None, item=item, branch=branches[1], movement_type=StockMovement.MovementType.IN, quantity=extra, reference="DEMO-INVENTORY", reason="Carga inicial demo sucursal alterna")
                    stock_2 = item.stock_records.get(branch=branches[1])
                    stock_2.minimum_stock = max(data["minimum"] / Decimal("2"), Decimal("1"))
                    stock_2.location_code = "Bodega B-02"
                    stock_2.save(update_fields=["minimum_stock", "location_code", "updated_at"])

        self.stdout.write(self.style.SUCCESS("Inventario demo creado correctamente."))
