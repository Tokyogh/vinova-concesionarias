"""ES: Este módulo expone tareas asíncronas y sus límites operativos para el dominio de ventas.

EN: This module exposes asynchronous tasks and their operational limits for the sales domain.

Contexto existente / Existing context:
Asynchronous task entry points for the sales domain.
"""

from celery import shared_task
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from apps.sales.models import SaleRecord
from apps.sales.services import expire_sale


@shared_task(name="apps.sales.tasks.expire_overdue_sales", ignore_result=False)
def expire_overdue_sales(batch_size: int = 200):
    now = timezone.now()
    ids = list(
        SaleRecord.objects.filter(is_deleted=False)
        .filter(
            Q(status=SaleRecord.Status.RESERVED, reserved_until__lte=now)
            | Q(status=SaleRecord.Status.QUOTED, valid_until__lt=now.date())
        )
        .order_by("reserved_until", "valid_until", "pk")
        .values_list("pk", flat=True)[: max(1, min(int(batch_size), 1000))]
    )
    expired = skipped = 0
    errors = []
    for sale_id in ids:
        try:
            sale = SaleRecord.objects.get(pk=sale_id, is_deleted=False)
            expire_sale(actor=None, sale=sale, note="Vencimiento automático de vigencia comercial")
            expired += 1
        except SaleRecord.DoesNotExist:
            skipped += 1
        except ValidationError as exc:
            skipped += 1
            errors.append({"sale_id": sale_id, "messages": exc.messages[:3]})
    return {"checked": len(ids), "expired": expired, "skipped": skipped, "errors": errors[:20]}
