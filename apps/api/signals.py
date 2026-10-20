"""ES: Este módulo implementa el componente signals para el dominio de API e integraciones.

EN: This module implements the signals component for the api domain.

Contexto existente / Existing context:
Django signal handlers for the api domain.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.api.services import publish_webhook_event
from apps.invoices.models import InvoiceRecord
from apps.leads.models import Lead
from apps.sales.models import SaleRecord
from apps.vehicles.models import Vehicle


@receiver(post_save, sender=Lead, dispatch_uid="api_webhook_lead")
def lead_webhook(sender, instance, created, raw=False, **kwargs):
    if raw:
        return
    publish_webhook_event(
        event_type="lead.created" if created else "lead.updated",
        aggregate_type="lead",
        aggregate_id=instance.public_id,
        branch=instance.branch,
        payload={
            "public_id": str(instance.public_id),
            "code": instance.code,
            "status": instance.status,
            "priority": instance.priority,
            "source": instance.source,
            "branch_id": instance.branch_id,
            "vehicle_id": instance.vehicle_id,
            "advisor_id": instance.assigned_advisor_id,
            "updated_at": instance.updated_at.isoformat() if instance.updated_at else "",
        },
    )


@receiver(post_save, sender=SaleRecord, dispatch_uid="api_webhook_sale")
def sale_webhook(sender, instance, created, raw=False, **kwargs):
    if raw:
        return
    publish_webhook_event(
        event_type="sale.created" if created else "sale.updated",
        aggregate_type="sale",
        aggregate_id=instance.pk,
        branch=instance.branch,
        payload={
            "id": instance.pk,
            "number": instance.number,
            "kind": instance.kind,
            "status": instance.status,
            "branch_id": instance.branch_id,
            "vehicle_id": instance.vehicle_id,
            "total": str(instance.total),
            "currency": "USD",
            "updated_at": instance.updated_at.isoformat() if instance.updated_at else "",
        },
    )


@receiver(post_save, sender=InvoiceRecord, dispatch_uid="api_webhook_invoice")
def invoice_webhook(sender, instance, created, raw=False, **kwargs):
    if raw:
        return
    publish_webhook_event(
        event_type="invoice.created" if created else "invoice.updated",
        aggregate_type="invoice",
        aggregate_id=instance.pk,
        branch=instance.branch,
        payload={
            "id": instance.pk,
            "number": instance.number,
            "invoice_type": instance.invoice_type,
            "status": instance.status,
            "branch_id": instance.branch_id,
            "total": str(instance.total),
            "currency": instance.currency,
            "issue_date": instance.issue_date.isoformat(),
            "updated_at": instance.updated_at.isoformat() if instance.updated_at else "",
        },
    )


@receiver(post_save, sender=Vehicle, dispatch_uid="api_webhook_vehicle")
def vehicle_webhook(sender, instance, created, raw=False, **kwargs):
    if raw:
        return
    publish_webhook_event(
        event_type="vehicle.created" if created else "vehicle.updated",
        aggregate_type="vehicle",
        aggregate_id=instance.pk,
        branch=instance.branch,
        payload={
            "id": instance.pk,
            "internal_code": instance.internal_code,
            "status": instance.status,
            "branch_id": instance.branch_id,
            "brand_id": instance.brand_id,
            "model_id": instance.model_id,
            "year": instance.year,
            "price": str(instance.price) if instance.price is not None else None,
            "updated_at": instance.updated_at.isoformat() if instance.updated_at else "",
        },
    )
