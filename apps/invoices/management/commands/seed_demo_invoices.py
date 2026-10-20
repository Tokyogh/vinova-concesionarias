"""ES: Implementa el comando administrativo «seed demo invoices» para facturación.

EN: Implements the «seed demo invoices» management command for invoices.

Contexto existente / Existing context:
Django management command for seed demo invoices.
"""

from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.invoices.models import InvoiceRecord
from apps.invoices.services import create_invoice_from_sale, issue_invoice
from apps.sales.models import SaleRecord


class Command(BaseCommand):
    help = "Crea un comprobante demo desde una operación comercial para validar facturación v0.12."

    @transaction.atomic
    def handle(self, *args, **options):
        actor = User.objects.filter(is_active=True, user_roles__role__code__in=["facturacion", "admin_general", "admin_sucursal"]).distinct().first() or User.objects.filter(is_active=True).first()
        sale = (
            SaleRecord.objects.filter(is_deleted=False, status__in=[SaleRecord.Status.SOLD, SaleRecord.Status.APPROVED, SaleRecord.Status.RESERVED])
            .select_related("customer", "branch", "vehicle")
            .first()
        )
        if not sale:
            self.stdout.write(self.style.WARNING("No hay ventas/reservas listas para facturar. Ejecuta primero seed_demo_sales."))
            return
        existing = InvoiceRecord.objects.filter(sale=sale, is_deleted=False).first()
        if existing:
            self.stdout.write(self.style.SUCCESS(f"Ya existe comprobante demo: {existing.number}"))
            return
        invoice = create_invoice_from_sale(
            actor=actor,
            sale=sale,
            invoice_type=InvoiceRecord.InvoiceType.INVOICE,
            issue_date=timezone.localdate(),
            due_date=timezone.localdate() + timedelta(days=15),
            notes="Comprobante demo generado desde una operación comercial.",
            internal_notes="Demo seguro: no corresponde a facturación tributaria real.",
        )
        if invoice.total > 0:
            try:
                issue_invoice(actor=actor, invoice=invoice, note="Emisión demo")
            except Exception:
                # Se mantiene como borrador si el entorno demo no permite emisión.
                pass
        self.stdout.write(self.style.SUCCESS(f"Comprobante demo creado: {invoice.number}"))
