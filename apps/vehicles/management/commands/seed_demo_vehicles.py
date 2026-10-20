"""ES: Implementa el comando administrativo «seed demo vehicles» para vehículos.

EN: Implements the «seed demo vehicles» management command for vehicles.

Contexto existente / Existing context:
Django management command for seed demo vehicles.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.branches.models import Branch
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel


DEMO_VEHICLES = [
    ("GMC", "Canyon", "Pickup", 2023, "AT4X", "VINDEMOGMCAT4X2023", "Rojo", Decimal("64990.00"), True),
    ("Foton", "Tunland", "Pickup", 2026, "G7 4x4", "VINDEMOFOTONG72026", "Blanco", Decimal("38990.00"), True),
    ("Chevrolet", "Colorado", "Pickup", 2025, "ZR2", "VINDEMOCOLORADO2025", "Gris", Decimal("58990.00"), False),
]


class Command(BaseCommand):
    help = "Crea marcas, modelos y vehículos demo para probar el catálogo público e interno."

    @transaction.atomic
    def handle(self, *args, **options):
        branch = Branch.objects.filter(is_active=True).order_by("id").first()
        created = 0
        for brand_name, model_name, segment, year, version, vin, color, price, featured in DEMO_VEHICLES:
            brand, _ = VehicleBrand.objects.update_or_create(name=brand_name, defaults={"is_active": True})
            model, _ = VehicleModel.objects.update_or_create(
                brand=brand,
                name=model_name,
                defaults={"segment": segment, "is_active": True},
            )
            slug = slugify(f"{year}-{brand_name}-{model_name}-{version}")
            vehicle, was_created = Vehicle.objects.update_or_create(
                vin=vin,
                defaults={
                    "brand": brand,
                    "model": model,
                    "branch": branch,
                    "year": year,
                    "version": version,
                    "color": color,
                    "mileage": 0,
                    "price": price,
                    "status": Vehicle.Status.AVAILABLE,
                    "published_at": timezone.now(),
                    "public_slug": slug,
                    "is_featured": featured,
                    "short_description": "Vehículo demo para validar presentación comercial y operación interna.",
                },
            )
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f"Vehículos demo listos. Nuevos creados: {created}."))
