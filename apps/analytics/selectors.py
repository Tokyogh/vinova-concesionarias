"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de analítica.

EN: This module implements authorization-aware read queries for the analytics domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the analytics domain.
"""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from apps.accounts.scopes import scope_queryset_to_user_branches
from apps.analytics.models import VehicleInteraction
from apps.customers.models import Customer
from apps.inventory.models import BranchStock
from apps.leads.models import Lead, LeadActivity
from apps.leads.selectors import scoped_lead_queryset
from apps.sales.models import SalePayment, SaleRecord


def _apply_range(qs, cleaned, field="created_at"):
    start = cleaned.get("start_date")
    end = cleaned.get("end_date")
    if start:
        qs = qs.filter(**{f"{field}__date__gte": start})
    if end:
        qs = qs.filter(**{f"{field}__date__lte": end})
    return qs


def filtered_commercial_leads(user, cleaned, *, permission_codes=("analytics.view",)):
    qs = _apply_range(scoped_lead_queryset(user, permission_codes=permission_codes), cleaned)
    if cleaned.get("branch"):
        qs = qs.filter(branch=cleaned["branch"])
    if cleaned.get("advisor"):
        qs = qs.filter(assigned_advisor=cleaned["advisor"])
    if cleaned.get("source"):
        qs = qs.filter(source=cleaned["source"])
    return qs


def filtered_interactions(user, cleaned, *, permission_codes=("analytics.view",)):
    qs = VehicleInteraction.objects.select_related("vehicle", "vehicle__brand", "vehicle__model", "branch", "lead")
    qs = _apply_range(
        scope_queryset_to_user_branches(
            qs,
            user=user,
            permission_codes=permission_codes,
        ),
        cleaned,
    )
    if cleaned.get("branch"):
        qs = qs.filter(branch=cleaned["branch"])
    return qs


def filtered_sales(user, cleaned, *, permission_codes=("analytics.view",)):
    qs = scope_queryset_to_user_branches(
        SaleRecord.objects.filter(is_deleted=False).select_related("branch", "advisor"),
        user=user,
        permission_codes=permission_codes,
    )
    qs = _apply_range(qs, cleaned)
    if cleaned.get("branch"):
        qs = qs.filter(branch=cleaned["branch"])
    if cleaned.get("advisor"):
        qs = qs.filter(advisor=cleaned["advisor"])
    return qs


def filtered_payments(user, cleaned, *, permission_codes=("analytics.view",)):
    qs = scope_queryset_to_user_branches(
        SalePayment.objects.filter(status=SalePayment.Status.CONFIRMED).select_related("sale", "sale__branch"),
        user=user,
        permission_codes=permission_codes,
        branch_lookup="sale__branch",
    )
    qs = _apply_range(qs, cleaned, "paid_at")
    if cleaned.get("branch"):
        qs = qs.filter(sale__branch=cleaned["branch"])
    if cleaned.get("advisor"):
        qs = qs.filter(sale__advisor=cleaned["advisor"])
    return qs


def _period_filters(cleaned):
    end = cleaned.get("end_date") or timezone.localdate()
    start = cleaned.get("start_date") or end.replace(day=1)
    return {**cleaned, "start_date": start, "end_date": end}


def commercial_dashboard_data(user, cleaned, *, permission_codes=("analytics.view",)):
    """Assemble branch-scoped commercial metrics for the requested period."""

    cleaned = _period_filters(cleaned)
    leads = filtered_commercial_leads(user, cleaned, permission_codes=permission_codes)
    interactions = filtered_interactions(user, cleaned, permission_codes=permission_codes)
    sales = filtered_sales(user, cleaned, permission_codes=permission_codes)
    sold_sales = sales.filter(status=SaleRecord.Status.SOLD)
    payments = filtered_payments(user, cleaned, permission_codes=permission_codes)
    customers = scope_queryset_to_user_branches(
        Customer.objects.filter(is_deleted=False),
        user=user,
        permission_codes=permission_codes,
        branch_lookup="assigned_branch",
    )
    customers = _apply_range(customers, cleaned)
    stock = scope_queryset_to_user_branches(
        BranchStock.objects.select_related("branch", "item"),
        user=user,
        permission_codes=permission_codes,
    )
    if cleaned.get("branch"):
        customers = customers.filter(assigned_branch=cleaned["branch"])
        stock = stock.filter(branch=cleaned["branch"])
    if cleaned.get("advisor"):
        customers = customers.filter(assigned_advisor=cleaned["advisor"])
    lead_summary = leads.aggregate(
        total=Count("id"),
        won=Count("id", filter=Q(status=Lead.Status.WON)),
        lost=Count("id", filter=Q(status=Lead.Status.LOST)),
        open=Count("id", filter=~Q(status__in=(Lead.Status.WON, Lead.Status.LOST))),
    )
    total = lead_summary["total"]
    won = lead_summary["won"]
    lost = lead_summary["lost"]
    decided = won + lost
    conversion = round((won / total * 100), 1) if total else 0
    close_rate = round((won / decided * 100), 1) if decided else 0
    open_leads = leads.exclude(status__in=[Lead.Status.WON, Lead.Status.LOST])
    overdue = open_leads.filter(next_follow_up_at__lt=timezone.now()).count()
    quote_count = leads.filter(Q(status=Lead.Status.QUOTED) | Q(linked_sale__isnull=False)).distinct().count()
    test_drive_count = leads.filter(test_drives__isnull=False).distinct().count()

    funnel_counts = dict(leads.values_list("status").annotate(count=Count("id")))
    funnel = [{"code": code, "label": label, "count": funnel_counts.get(code, 0)} for code, label in Lead.Status.choices]
    max_funnel = max([row["count"] for row in funnel] or [1])
    for row in funnel:
        row["percent"] = round(row["count"] / max_funnel * 100, 1) if max_funnel else 0

    vehicles = list(
        leads.filter(vehicle__isnull=False)
        .values("vehicle_id", "vehicle__internal_code", "vehicle__brand__name", "vehicle__model__name", "vehicle__year")
        .annotate(leads=Count("id"), won=Count("id", filter=Q(status=Lead.Status.WON)))
        .order_by("-leads", "vehicle__brand__name")[:12]
    )
    click_map = {
        row["vehicle_id"]: row["clicks"]
        for row in interactions.filter(vehicle__isnull=False).values("vehicle_id").annotate(clicks=Count("id"))
    }
    for row in vehicles:
        row["clicks"] = click_map.get(row["vehicle_id"], 0)
        row["conversion"] = round(row["won"] / row["leads"] * 100, 1) if row["leads"] else 0

    cities = list(
        leads.exclude(city="").values("city", "province").annotate(leads=Count("id"), won=Count("id", filter=Q(status=Lead.Status.WON))).order_by("-leads", "city")[:15]
    )
    sources = list(
        leads.values("source").annotate(leads=Count("id"), won=Count("id", filter=Q(status=Lead.Status.WON))).order_by("-leads")
    )
    source_labels = dict(Lead.Source.choices)
    for row in sources:
        row["label"] = source_labels.get(row["source"], row["source"])
        row["conversion"] = round(row["won"] / row["leads"] * 100, 1) if row["leads"] else 0

    advisors = list(
        leads.filter(assigned_advisor__isnull=False)
        .values("assigned_advisor_id", "assigned_advisor__username", "assigned_advisor__first_name", "assigned_advisor__last_name")
        .annotate(leads=Count("id"), won=Count("id", filter=Q(status=Lead.Status.WON)), quotes=Count("id", filter=Q(linked_sale__isnull=False)))
        .order_by("-won", "-leads")[:15]
    )
    for row in advisors:
        row["display"] = " ".join(filter(None, [row["assigned_advisor__first_name"], row["assigned_advisor__last_name"]])) or row["assigned_advisor__username"]
        row["conversion"] = round(row["won"] / row["leads"] * 100, 1) if row["leads"] else 0

    sales_summary = sold_sales.aggregate(count=Count("id"), total=Coalesce(Sum("total"), Decimal("0.00")))
    payments_total = payments.aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]
    balance_total = sales.filter(
        status__in=(SaleRecord.Status.RESERVED, SaleRecord.Status.APPROVED, SaleRecord.Status.SOLD),
        balance_due__gt=0,
    ).aggregate(total=Coalesce(Sum("balance_due"), Decimal("0.00")))["total"]
    stock_summary = stock.aggregate(records=Count("id"), units=Coalesce(Sum("quantity"), Decimal("0.00")))
    low_stock = stock.filter(item__track_stock=True, minimum_stock__gt=0, quantity__lte=F("minimum_stock")).count()
    activities = LeadActivity.objects.filter(lead__in=leads)
    sales_trend = list(
        sold_sales.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"), total=Sum("total"))
        .order_by("day")
    )
    branch_performance = list(
        sold_sales.values("branch_id", "branch__name")
        .annotate(sales=Count("id"), total=Sum("total"))
        .order_by("-total")[:12]
    )
    period_days = (cleaned["end_date"] - cleaned["start_date"]).days + 1
    previous = {
        **cleaned,
        "start_date": cleaned["start_date"] - timezone.timedelta(days=period_days),
        "end_date": cleaned["start_date"] - timezone.timedelta(days=1),
    }
    previous_sales = filtered_sales(user, previous, permission_codes=permission_codes).filter(status=SaleRecord.Status.SOLD)
    previous_total = previous_sales.aggregate(total=Coalesce(Sum("total"), Decimal("0.00")))["total"]
    sales_change = round((sales_summary["total"] - previous_total) / previous_total * 100, 1) if previous_total else None
    return {
        "metrics": {
            "total": total, "open": lead_summary["open"], "won": won, "lost": lost, "conversion": conversion,
            "close_rate": close_rate, "overdue": overdue, "quotes": quote_count, "test_drives": test_drive_count,
            "interactions": interactions.count(), "sales_count": sales_summary["count"],
            "sales_total": sales_summary["total"], "payments_total": payments_total,
            "balance_total": balance_total, "customers": customers.count(),
            "stock_records": stock_summary["records"], "stock_units": stock_summary["units"],
            "low_stock": low_stock, "activities": activities.count(),
            "previous_sales_total": previous_total, "sales_change": sales_change,
        },
        "funnel": funnel, "vehicles": vehicles, "cities": cities, "sources": sources, "advisors": advisors,
        "sales_trend": sales_trend, "branch_performance": branch_performance,
        "recent_leads": leads[:10], "recent_activity": activities.select_related("lead", "created_by")[:10],
    }
