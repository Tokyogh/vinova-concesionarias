"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de ventas.

EN: This module implements authorization-aware read queries for the sales domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the sales domain.
"""

from __future__ import annotations

from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.accounts.scopes import scope_queryset_to_user_branches
from apps.sales.models import SalePayment, SaleRecord

SALES_SCOPE_PERMISSIONS = ("sales.quote", "sales.reserve", "sales.sell")


def accessible_sales_queryset(user):
    return scope_queryset_to_user_branches(
        SaleRecord.objects.filter(is_deleted=False), user=user,
        permission_codes=SALES_SCOPE_PERMISSIONS, branch_lookup="branch",
    )


def sale_list_queryset(user, *, query: str = "", status: str = "", kind: str = "", branch=None, sort: str = ""):
    qs = (
        accessible_sales_queryset(user)
        .select_related("customer", "branch", "advisor", "vehicle", "vehicle__brand", "vehicle__model", "vehicle__model__brand")
        .annotate(line_count=Count("lines", distinct=True))
    )
    if query:
        qs = qs.filter(
            Q(number__icontains=query)
            | Q(customer__first_name__icontains=query)
            | Q(customer__last_name__icontains=query)
            | Q(customer__business_name__icontains=query)
            | Q(customer__identification_number__icontains=query)
            | Q(vehicle__internal_code__icontains=query) | Q(vehicle__vin__icontains=query)
            | Q(vehicle__plate__icontains=query)
            | Q(vehicle__brand__name__icontains=query)
            | Q(vehicle__model__name__icontains=query)
        )
    if status:
        qs = qs.filter(status=status)
    if kind:
        qs = qs.filter(kind=kind)
    if branch:
        qs = qs.filter(branch=branch)
    ordering = {
        "oldest": ("created_at",), "total_desc": ("-total", "-created_at"),
        "total_asc": ("total", "-created_at"),
    }.get(sort, ("-created_at",))
    return qs.order_by(*ordering)


def sale_detail_queryset(user):
    return (
        accessible_sales_queryset(user)
        .select_related("customer", "branch", "advisor", "created_by", "vehicle", "vehicle__brand", "vehicle__model", "vehicle__branch")
        .prefetch_related("lines__item", "payments", "status_history__changed_by")
    )


def sale_lines_queryset(sale):
    return sale.lines.select_related("item", "item__category").order_by("id")


def sale_payments_queryset(sale):
    return sale.payments.select_related("received_by").order_by("-paid_at", "-created_at")


def sale_status_history_queryset(sale):
    return sale.status_history.select_related("changed_by").order_by("-created_at")


def sales_metrics(user):
    current_month = timezone.now().date().replace(day=1)
    base = accessible_sales_queryset(user)
    open_statuses = [SaleRecord.Status.DRAFT, SaleRecord.Status.QUOTED, SaleRecord.Status.RESERVED, SaleRecord.Status.APPROVED]
    return {
        "open": base.filter(status__in=open_statuses).count(),
        "quoted": base.filter(status=SaleRecord.Status.QUOTED).count(),
        "reserved": base.filter(status=SaleRecord.Status.RESERVED).count(),
        "sold_month": base.filter(status=SaleRecord.Status.SOLD, closed_at__date__gte=current_month).count(),
        "revenue_month": base.filter(status=SaleRecord.Status.SOLD, closed_at__date__gte=current_month).aggregate(total=Sum("total"))["total"] or 0,
        "pending_balance": base.filter(status__in=[SaleRecord.Status.RESERVED, SaleRecord.Status.APPROVED, SaleRecord.Status.SOLD]).aggregate(total=Sum("balance_due"))["total"] or 0,
        "payments_month": SalePayment.objects.filter(sale_id__in=base.values("pk"), status=SalePayment.Status.CONFIRMED, paid_at__date__gte=current_month).aggregate(total=Sum("amount"))["total"] or 0,
    }


def sales_needing_attention_queryset(user):
    now = timezone.now()
    return (
        accessible_sales_queryset(user)
        .filter(Q(status=SaleRecord.Status.RESERVED, reserved_until__lt=now) | Q(status=SaleRecord.Status.QUOTED, valid_until__lt=now.date()))
        .select_related("customer", "branch", "vehicle", "vehicle__brand", "vehicle__model", "vehicle__model__brand")
        .order_by("reserved_until", "valid_until")
    )
