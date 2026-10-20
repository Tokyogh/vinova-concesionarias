"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de postventa.

EN: This module implements business services and transactional effects for the post sales domain.

Contexto existente / Existing context:
Transactional business services for the post sales domain.
"""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.scopes import accessible_branch_ids
from apps.audit.services import audit_log
from apps.common.modules import is_module_enabled
from apps.post_sales.models import ServiceOrder, ServiceOrderHistory, ServiceOrderLine


TRANSITIONS = {
    ServiceOrder.Status.DRAFT: {ServiceOrder.Status.SCHEDULED, ServiceOrder.Status.CANCELLED},
    ServiceOrder.Status.SCHEDULED: {ServiceOrder.Status.IN_PROGRESS, ServiceOrder.Status.CANCELLED},
    ServiceOrder.Status.IN_PROGRESS: {ServiceOrder.Status.COMPLETED, ServiceOrder.Status.CANCELLED},
    ServiceOrder.Status.COMPLETED: set(),
    ServiceOrder.Status.CANCELLED: set(),
}


def _require_enabled():
    if not is_module_enabled("post_sales"):
        raise ValidationError("El módulo de postventa está desactivado.")


def _require_branch(actor, branch_id, permission="post_sales.manage"):
    branch_ids = accessible_branch_ids(actor, permission_codes=(permission,))
    if branch_ids is not None and branch_id not in branch_ids:
        raise PermissionDenied("No tienes alcance sobre esta sucursal.")


@transaction.atomic
def create_service_order(*, actor, form):
    _require_enabled()
    order = form.save(commit=False)
    _require_branch(actor, order.branch_id)
    order.created_by = actor
    order.calculate_total()
    order.full_clean()
    order.save()
    form.save_m2m()
    ServiceOrderHistory.objects.create(
        order=order,
        new_status=order.status,
        changed_by=actor,
        note="Orden creada",
        snapshot={"total_cost": str(order.total_cost)},
    )
    audit_log(user=actor, action="post_sales.order_created", target=order, branch=order.branch)
    return order


@transaction.atomic
def transition_service_order(*, actor, order_id, new_status, note=""):
    """ES: Ejecuta la operación «transition service order» dentro del dominio de postventa. Además, conserva atomicidad y bloqueos explícitos, registra efectos auditables, rechaza estados o entradas inválidas.

    EN: Executes the «transition service order» operation within the post sales domain. It also preserves atomicity and explicit locking, records auditable effects, rejects invalid input or state.
    """

    _require_enabled()
    order = (
        ServiceOrder.objects.select_for_update()
        .select_related("branch", "customer", "vehicle")
        .get(pk=order_id)
    )
    _require_branch(actor, order.branch_id)
    if new_status not in TRANSITIONS.get(order.status, set()):
        raise ValidationError("Transición de estado no permitida.")
    previous = order.status
    note = (note or "").strip()
    if new_status == ServiceOrder.Status.CANCELLED and not note:
        raise ValidationError("Debes registrar el motivo de cancelación.")
    order.status = new_status
    if new_status == ServiceOrder.Status.IN_PROGRESS and not order.started_at:
        order.started_at = timezone.now()
    if new_status == ServiceOrder.Status.COMPLETED:
        order.completed_at = timezone.now()
    if new_status == ServiceOrder.Status.CANCELLED:
        order.cancelled_at = timezone.now()
        order.cancellation_reason = note[:220]
    order.save(
        update_fields=[
            "status",
            "started_at",
            "completed_at",
            "cancelled_at",
            "cancellation_reason",
            "updated_at",
        ]
    )
    ServiceOrderHistory.objects.create(
        order=order,
        previous_status=previous,
        new_status=new_status,
        changed_by=actor,
        note=note,
        snapshot={"total_cost": str(order.total_cost)},
    )
    audit_log(
        user=actor,
        action="post_sales.status_changed",
        target=order,
        branch=order.branch,
        before={"status": previous},
        after={"status": new_status},
    )
    from apps.notifications.services import schedule_customer_event_notification

    schedule_customer_event_notification(
        customer=order.customer,
        title=f"Servicio actualizado: {order.get_status_display()}",
        body=f"La orden de servicio {order.pk} para {order.vehicle} cambió a {order.get_status_display()}.",
        message_type="maintenance",
        dedup_key=f"service-order:{order.pk}:status:{new_status}",
        actor=actor,
        priority="high" if new_status == ServiceOrder.Status.CANCELLED else "normal",
        branch=order.branch,
        related_vehicle=order.vehicle,
    )
    return order


@transaction.atomic
def update_service_order_operational_details(*, actor, order_id, form):
    _require_enabled()
    order = ServiceOrder.objects.select_for_update().select_related("branch", "vehicle").get(pk=order_id)
    _require_branch(actor, order.branch_id)
    before = {
        field: getattr(order, field)
        for field in (
            "scheduled_at",
            "reception_mileage",
            "delivery_mileage",
            "diagnosis",
            "next_service_date",
            "next_service_mileage",
        )
    }
    for field in before:
        setattr(order, field, form.cleaned_data[field])
    order.full_clean()
    order.save(update_fields=[*before.keys(), "updated_at"])
    audit_log(
        user=actor,
        action="post_sales.operational_details_updated",
        target=order,
        branch=order.branch,
        before=before,
        after={field: getattr(order, field) for field in before},
    )
    return order


def _recalculate_order_costs(order):
    grouped = {
        row["line_type"]: row["total"]
        for row in order.lines.values("line_type").annotate(total=Sum("total_cost"))
    }
    order.labor_cost = sum(
        (grouped.get(ServiceOrderLine.LineType.SERVICE, 0), grouped.get(ServiceOrderLine.LineType.LABOR, 0))
    )
    order.parts_cost = grouped.get(ServiceOrderLine.LineType.PART, 0)
    order.external_cost = grouped.get(ServiceOrderLine.LineType.EXTERNAL, 0)
    order.calculate_total()
    order.save(update_fields=["labor_cost", "parts_cost", "external_cost", "total_cost", "updated_at"])


@transaction.atomic
def add_service_order_line(*, actor, order_id, form):
    _require_enabled()
    order = ServiceOrder.objects.select_for_update().select_related("branch").get(pk=order_id)
    _require_branch(actor, order.branch_id)
    if order.status in (ServiceOrder.Status.COMPLETED, ServiceOrder.Status.CANCELLED):
        raise ValidationError("No se pueden modificar servicios de una orden cerrada.")
    line = form.save(commit=False)
    line.order = order
    line.calculate_total()
    line.full_clean()
    line.save()
    _recalculate_order_costs(order)
    audit_log(
        user=actor,
        action="post_sales.line_added",
        target=order,
        branch=order.branch,
        metadata={"line_id": line.pk, "line_type": line.line_type, "total_cost": str(line.total_cost)},
    )
    return line
