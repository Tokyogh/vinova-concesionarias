"""ES: Implementa el comando administrativo «seed demo sales» para ventas.

EN: Implements the «seed demo sales» management command for sales.

Contexto existente / Existing context:
Django management command for seed demo sales.
"""

from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.branches.models import Branch
from apps.customers.models import Customer
from apps.inventory.models import InventoryItem
from apps.sales.models import SaleLine, SalePayment, SaleRecord
from apps.sales.services import create_status_history, recalculate_sale_totals, reserve_sale
from apps.vehicles.models import Vehicle


class Command(BaseCommand):
    """ES: Agrupa el componente «command» del dominio de ventas y sus reglas relacionadas. Además, conserva atomicidad y bloqueos explícitos.

    EN: Groups the «command» component and its related rules in the sales domain. It also preserves atomicity and explicit locking.
    """

    help = "Crea cotizaciones, reservas y pagos demo para validar ventas v0.8."

    @transaction.atomic
    def handle(self, *args, **options):
        """ES: Orquesta «seed demo sales» con fallos controlados para ventas.

        EN: Orchestrates «seed demo sales» with controlled failures for sales.
        """

        branch = Branch.objects.filter(is_active=True).first()
        customer = Customer.objects.filter(is_deleted=False).first()
        advisor = User.objects.filter(is_active=True, user_roles__role__code__in=["vendedor", "admin_sucursal", "admin_general"]).distinct().first() or User.objects.filter(is_active=True).first()
        vehicle = Vehicle.objects.filter(is_deleted=False, status=Vehicle.Status.AVAILABLE).select_related("brand", "model").first()
        item = InventoryItem.objects.filter(is_deleted=False, status=InventoryItem.Status.ACTIVE).first()

        if not branch or not customer:
            self.stdout.write(self.style.WARNING("Faltan sucursal o cliente. Ejecuta primero seed_demo_organization y seed_demo_customers."))
            return

        sale, created = SaleRecord.objects.get_or_create(
            number="COT-DEMO-0001",
            defaults={
                "kind": SaleRecord.Kind.QUOTE,
                "status": SaleRecord.Status.QUOTED,
                "customer": customer,
                "branch": branch,
                "advisor": advisor,
                "vehicle": vehicle,
                "source": SaleRecord.Source.SHOWROOM,
                "vehicle_price": vehicle.price if vehicle and vehicle.price else 0,
                "vehicle_discount": 500 if vehicle else 0,
                "valid_until": timezone.localdate() + timedelta(days=7),
                "reserved_until": timezone.now() + timedelta(days=3),
                "notes": "Cotización demo creada para validar el flujo comercial.",
                "internal_notes": "Puede pasar a reserva o venta desde el detalle.",
                "created_by": advisor,
            },
        )
        if created:
            create_status_history(sale=sale, new=sale.status, actor=advisor, note="Cotización demo creada")
        if item and not sale.lines.exists():
            line = SaleLine(sale=sale, item=item, description=item.name, quantity=1, unit_price=item.price, discount_amount=0)
            line.calculate_totals()
            line.save()
        recalculate_sale_totals(sale)

        reserved_vehicle = Vehicle.objects.filter(is_deleted=False, status=Vehicle.Status.AVAILABLE).exclude(pk=vehicle.pk if vehicle else None).first()
        if reserved_vehicle:
            reservation, created_res = SaleRecord.objects.get_or_create(
                number="RES-DEMO-0001",
                defaults={
                    "kind": SaleRecord.Kind.RESERVATION,
                    "status": SaleRecord.Status.QUOTED,
                    "customer": customer,
                    "branch": reserved_vehicle.branch or branch,
                    "advisor": advisor,
                    "vehicle": reserved_vehicle,
                    "source": SaleRecord.Source.WHATSAPP,
                    "vehicle_price": reserved_vehicle.price or 0,
                    "reserved_until": timezone.now() + timedelta(days=2),
                    "notes": "Reserva demo para validar cambio de estado del vehículo.",
                    "created_by": advisor,
                },
            )
            if created_res:
                create_status_history(sale=reservation, new=reservation.status, actor=advisor, note="Reserva demo creada")
                reserve_sale(actor=advisor, sale=reservation, reserved_until=reservation.reserved_until, note="Reserva demo")
            recalculate_sale_totals(reservation)

        if not sale.payments.exists() and sale.total > 0:
            payment = SalePayment(sale=sale, method=SalePayment.Method.TRANSFER, amount=min(sale.total, sale.total / 2), reference="DEMO-PAGO", received_by=advisor)
            payment.full_clean()
            payment.save()
            recalculate_sale_totals(sale)

        self.stdout.write(self.style.SUCCESS("Ventas, cotizaciones y reservas demo creadas correctamente."))
