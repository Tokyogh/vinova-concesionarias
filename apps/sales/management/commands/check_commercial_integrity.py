"""ES: Implementa el comando administrativo «check commercial integrity» para ventas.

EN: Implements the «check commercial integrity» management command for sales.

Contexto existente / Existing context:
Django management command for check commercial integrity.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

from apps.sales.models import SaleRecord


class Command(BaseCommand):
    help = "Valida precondiciones de integridad comercial sin modificar datos."

    def handle(self, *args, **options):
        missing_expiry = list(SaleRecord.objects.filter(
            is_deleted=False, status=SaleRecord.Status.RESERVED, reserved_until__isnull=True,
        ).values_list("number", flat=True)[:20])
        duplicates = list(SaleRecord.objects.filter(
            is_deleted=False, vehicle_id__isnull=False,
            status__in=[SaleRecord.Status.RESERVED, SaleRecord.Status.SOLD],
        ).values("vehicle_id").annotate(total=Count("id")).filter(total__gt=1).values_list("vehicle_id", "total")[:20])
        problems = []
        if missing_expiry:
            problems.append("reservas sin vencimiento: " + ", ".join(missing_expiry))
        if duplicates:
            problems.append("unidades duplicadas: " + ", ".join(f"vehicle_id={pk} ({total})" for pk, total in duplicates))
        if problems:
            raise CommandError("Integridad comercial no apta para migrar. " + " | ".join(problems))
        self.stdout.write(self.style.SUCCESS("Integridad comercial validada."))
