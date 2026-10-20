"""ES: Este módulo implementa el componente sale lifecycle para el dominio de CRM y leads.

EN: This module implements the sale lifecycle component for the leads domain.

Contexto existente / Existing context:
Sale lifecycle support for the leads domain.
"""

from __future__ import annotations

from django.utils import timezone

from apps.audit.services import audit_log
from apps.leads.models import Lead, LeadActivity
from apps.sales.models import SaleRecord


def sync_origin_leads_for_sale(*, actor, sale: SaleRecord) -> int:
    """Synchronize CRM state after a commercial transition.

    The caller owns the surrounding transaction and has already locked the sale.
    Lock origin leads independently so the nullable SaleRecord relationship is
    never part of a ``SELECT ... FOR UPDATE`` join.
    """

    leads = list(
        Lead.objects.select_for_update()
        .filter(linked_sale_id=sale.pk, is_deleted=False)
        .order_by("pk")
    )
    changed = 0
    now = timezone.now()

    for lead in leads:
        previous = lead.status
        if sale.status == SaleRecord.Status.RESERVED and not lead.is_closed:
            lead.status = Lead.Status.NEGOTIATION
            lead.closed_at = None
        elif sale.status == SaleRecord.Status.SOLD:
            lead.status = Lead.Status.WON
            lead.closed_at = now
            lead.next_follow_up_at = None
            lead.lost_reason = ""
        elif sale.status in {SaleRecord.Status.CANCELLED, SaleRecord.Status.EXPIRED} and not lead.is_closed:
            lead.status = Lead.Status.INTERESTED
            lead.closed_at = None
            lead.lost_reason = ""
        else:
            continue

        if lead.status == previous:
            continue

        lead.save(
            update_fields=[
                "status",
                "closed_at",
                "next_follow_up_at",
                "lost_reason",
                "updated_at",
            ]
        )
        # Imported lazily to keep the sales/services -> lifecycle dependency
        # from creating a module import cycle with leads/services -> sales/services.
        from apps.leads.services import refresh_lead_score

        refresh_lead_score(lead)
        LeadActivity.objects.create(
            lead=lead,
            activity_type=LeadActivity.ActivityType.STATUS,
            title=f"Operación {sale.number}: {sale.get_status_display()}",
            detail="Estado sincronizado desde el ciclo comercial.",
            previous_status=previous,
            new_status=lead.status,
            created_by=actor if getattr(actor, "is_authenticated", False) else None,
            metadata={
                "sale_id": sale.pk,
                "sale_number": sale.number,
                "sale_status": sale.status,
            },
        )
        audit_log(
            user=actor,
            action="leads.sale_status_sync",
            target=lead,
            before={"status": previous, "sale": sale.pk},
            after={"status": lead.status, "sale": sale.pk},
        )
        changed += 1

    return changed
