"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de paneles.

EN: This module implements authorization-aware read queries for the dashboard domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the dashboard domain.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.urls import reverse

from apps.accounts.scopes import accessible_branch_ids
from apps.audit.models import SecurityAlert
from apps.analytics.models import VehicleInteraction
from apps.audit.selectors import scoped_alert_queryset, scoped_audit_queryset
from apps.accounts.models import User
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer, CustomerNote, CustomerVehicleInterest
from apps.customers.selectors import accessible_customer_queryset
from apps.documents.models import PrivateDocument, ReusableAsset
from apps.documents.selectors import private_documents_queryset
from apps.inventory.models import BranchStock, InventoryItem, StockMovement
from apps.inventory.selectors import stock_movements_queryset
from apps.invoices.models import InvoiceRecord
from apps.invoices.selectors import accessible_invoices_queryset
from apps.notifications.models import NotificationMessage, NotificationRecipient, NotificationTemplate
from apps.leads.models import Lead
from apps.leads.selectors import scoped_lead_queryset
from apps.sales.models import SalePayment, SaleRecord
from apps.sales.selectors import accessible_sales_queryset, sales_needing_attention_queryset
from apps.vehicles.models import Vehicle
from apps.vehicles.selectors import public_vehicle_queryset
from apps.enterprise.selectors import get_primary_company, get_public_settings


def dashboard_metrics():
    """Legacy/global metrics kept for compatibility with previous tests."""

    key = "dashboard:metrics:v11"
    data = cache.get(key)
    if data:
        return data
    data = {
        "active_companies": Company.objects.filter(is_active=True).count(),
        "active_branches": Branch.objects.filter(is_active=True).count(),
        "active_users": User.objects.filter(is_active=True).count(),
        "available_vehicles": Vehicle.objects.filter(status=Vehicle.Status.AVAILABLE, is_deleted=False).count(),
        "reserved_vehicles": Vehicle.objects.filter(status=Vehicle.Status.RESERVED, is_deleted=False).count(),
        "sold_vehicles": Vehicle.objects.filter(status=Vehicle.Status.SOLD, is_deleted=False).count(),
        "featured_vehicles": Vehicle.objects.filter(is_featured=True, is_deleted=False).count(),
        "customers_total": Customer.objects.filter(is_deleted=False).count(),
        "customers_prospect": Customer.objects.filter(status=Customer.Status.PROSPECT, is_deleted=False).count(),
        "customers_active": Customer.objects.filter(status__in=[Customer.Status.ACTIVE, Customer.Status.VIP], is_deleted=False).count(),
    }
    cache.set(key, data, 60)
    return data


def public_home_context():
    """Datos seguros para la portada pública."""

    vehicles_qs = public_vehicle_queryset()
    branches_qs = Branch.objects.filter(is_active=True).select_related("company")
    featured = list(vehicles_qs.filter(is_featured=True)[:6])
    latest = list(vehicles_qs[:6])
    company = get_primary_company()
    public_settings = get_public_settings(company) if company else None
    return {
        "company": company,
        "public_settings": public_settings,
        "featured_vehicles": featured,
        "latest_vehicles": latest,
        "display_vehicles": featured or latest,
        "public_vehicle_count": vehicles_qs.count(),
        "public_brand_count": vehicles_qs.values("brand_id").distinct().count(),
        "public_model_count": vehicles_qs.values("model_id").distinct().count(),
        "public_branch_count": branches_qs.count(),
        "public_branches": branches_qs[:4],
    }


def _branch_filter(user):
    branch = getattr(user, "branch", None)
    return branch


MONTH_LABELS = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")


def _shift_month(anchor, offset):
    """Desplaza un primer día de mes sin depender de aritmética de días."""

    index = anchor.year * 12 + (anchor.month - 1) + offset
    return date(index // 12, index % 12 + 1, 1)


def _percent_delta(current, previous):
    """Variación porcentual segura ante divisor cero."""

    current = float(current or 0)
    previous = float(previous or 0)
    if previous <= 0:
        return 100.0 if current > 0 else 0.0
    return round((current - previous) / previous * 100, 1)


def _evolution_series(sales_qs, month_anchor, months):
    """Cuenta ventas por mes con una sola consulta (TruncMonth)."""

    oldest = _shift_month(month_anchor, -(months - 1))
    oldest_aware = timezone.make_aware(datetime.combine(oldest, time.min), timezone.get_current_timezone())
    series = {offset: 0 for offset in range(months - 1, -1, -1)}
    rows = (
        sales_qs.filter(created_at__gte=oldest_aware)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
    )
    for row in rows:
        month_value = row["month"]
        if month_value is None:
            continue
        offset = (
            month_value.year * 12 + (month_value.month - 1) - (month_anchor.year * 12 + (month_anchor.month - 1))
        )
        if offset in series:
            series[offset] = row["count"]
    evolution = []
    for offset in sorted(series):
        month_date = _shift_month(month_anchor, offset)
        evolution.append({
            "label": MONTH_LABELS[month_date.month - 1],
            "count": series[offset],
            "is_current": offset == 0,
        })
    peak = max((item["count"] for item in evolution), default=0) or 1
    for item in evolution:
        item["height"] = max(6, round(item["count"] / peak * 100))
    return evolution


def executive_summary_context(user, *, months: int = 6):
    """Resumen ejecutivo: KPIs del periodo, evolución mensual y actividad real.

    Todos los valores provienen de la base y respetan la sucursal asignada al
    usuario y sus permisos; no se inventan cifras ni se usan datos de otras
    sucursales.
    """

    period_start = timezone.now() - timedelta(days=30)
    previous_start = timezone.now() - timedelta(days=60)
    branch = _branch_filter(user)
    branch_filter = {"branch": branch} if branch else {}

    can_view_sales = user.has_perm_code("sales.view") or user.has_perm_code("sales.manage")
    sales_qs = SaleRecord.objects.filter(is_deleted=False, **branch_filter)
    sales_current = sales_qs.filter(created_at__gte=period_start) if can_view_sales else sales_qs.none()
    sales_previous = sales_qs.filter(created_at__gte=previous_start, created_at__lt=period_start) if can_view_sales else sales_qs.none()

    sold_statuses = [SaleRecord.Status.SOLD]

    if can_view_sales:
        current_agg = sales_current.aggregate(
            count=Count("id"),
            revenue=Sum("total", filter=Q(status__in=sold_statuses)),
        )
        previous_agg = sales_previous.aggregate(
            count=Count("id"),
            revenue=Sum("total", filter=Q(status__in=sold_statuses)),
        )
        reservations_agg = sales_qs.filter(status=SaleRecord.Status.RESERVED).aggregate(
            total=Count("id"),
            current=Count("id", filter=Q(updated_at__gte=period_start)),
        )
    else:
        current_agg = {"count": 0, "revenue": None}
        previous_agg = {"count": 0, "revenue": None}
        reservations_agg = {"total": 0, "current": 0}

    revenue_current = current_agg["revenue"] or Decimal("0.00")
    revenue_previous = previous_agg["revenue"] or Decimal("0.00")
    sales_current_count = current_agg["count"]
    sales_previous_count = previous_agg["count"]
    reservations_current = reservations_agg["current"]
    reservations_total = reservations_agg["total"]

    lead_qs = scoped_lead_queryset(user) if user.can_view_leads else Lead.objects.none()
    leads_total = lead_qs.count()
    converted = sales_qs.filter(customer__crm_leads__isnull=False).distinct().count() if can_view_sales else 0
    conversion = round(converted / leads_total * 100, 1) if leads_total else 0.0

    kpis = [
        {
            "key": "sales",
            "label": "Ventas del periodo",
            "value": sales_current_count,
            "delta": _percent_delta(sales_current_count, sales_previous_count),
            "hint": "Documentos creados en los últimos 30 días",
            "tone": "primary",
        },
        {
            "key": "revenue",
            "label": "Ingresos confirmados",
            "value": revenue_current,
            "delta": _percent_delta(revenue_current, revenue_previous),
            "hint": "Suma de ventas en estado vendido",
            "tone": "success",
            "is_currency": True,
        },
        {
            "key": "reservations",
            "label": "Reservas activas",
            "value": reservations_current,
            "delta": _percent_delta(reservations_current, reservations_total),
            "hint": "Documentos reservados con vigencia",
            "tone": "warning",
        },
        {
            "key": "conversion",
            "label": "Conversión comercial",
            "value": conversion,
            "delta": _percent_delta(conversion, 0.0),
            "hint": "Clientes con lead frente a leads totales",
            "tone": "violet",
            "is_percent": True,
        },
    ]

    # Evolución mensual de ventas (barras CSS, sin dependencias JS).
    month_anchor = timezone.localdate().replace(day=1)
    if can_view_sales:
        evolution = _evolution_series(sales_qs, month_anchor, months)
    else:
        evolution = [
            {"label": MONTH_LABELS[_shift_month(month_anchor, -offset).month - 1], "count": 0, "is_current": offset == 0, "height": 6}
            for offset in range(months - 1, -1, -1)
        ]

    activity = []
    if can_view_sales:
        for sale in sales_qs.select_related("customer", "branch").order_by("-created_at")[:5]:
            activity.append({
                "kind": "Venta",
                "title": sale.number,
                "detail": getattr(sale.customer, "display_name", "") or sale.customer.full_name,
                "meta": getattr(sale.branch, "name", ""),
                "at": sale.created_at,
            })
    if user.can_view_leads:
        for lead in lead_qs.order_by("-created_at")[:5]:
            activity.append({
                "kind": "Lead",
                "title": lead.code or lead.public_id.hex[:8],
                "detail": lead.full_name,
                "meta": lead.get_status_display(),
                "at": lead.created_at,
            })
    activity.sort(key=lambda item: item["at"], reverse=True)

    return {
        "executive_kpis": kpis,
        "executive_evolution": evolution,
        "executive_activity": activity[:6],
        "executive_has_sales": can_view_sales,
        "executive_has_leads": bool(user.can_view_leads),
    }


def admin_dashboard_context(user):
    metrics = dashboard_metrics()
    sales_agg = SaleRecord.objects.filter(is_deleted=False).aggregate(
        sales_total=Count("id"),
        sales_sold=Count("id", filter=Q(status=SaleRecord.Status.SOLD)),
    )
    leads_agg = Lead.objects.filter(is_deleted=False).aggregate(
        leads_total=Count("id"),
        leads_open=Count("id", filter=~Q(status__in=[Lead.Status.WON, Lead.Status.LOST])),
    )
    metrics.update(
        {
            "sales_total": sales_agg["sales_total"],
            "sales_sold": sales_agg["sales_sold"],
            "documents_total": PrivateDocument.objects.filter(is_deleted=False).count(),
            "assets_total": ReusableAsset.objects.filter(is_deleted=False).count(),
            "notifications_sent": NotificationMessage.objects.filter(is_deleted=False).count(),
            "templates_total": NotificationTemplate.objects.filter(is_deleted=False).count(),
            "invoices_total": InvoiceRecord.objects.filter(is_deleted=False).count(),
            "leads_total": leads_agg["leads_total"],
            "leads_open": leads_agg["leads_open"],
            "catalog_interactions": VehicleInteraction.objects.count(),
        }
    )
    return {
        "metrics": metrics,
        "recent_sales": SaleRecord.objects.filter(is_deleted=False).select_related("customer", "branch", "vehicle", "vehicle__brand", "vehicle__model", "vehicle__model__brand")[:6],
        "recent_documents": PrivateDocument.objects.filter(is_deleted=False).select_related("customer", "vehicle", "sale")[:6],
        "recent_notifications": NotificationMessage.objects.filter(is_deleted=False).select_related("sender")[:6],
    }


def branch_dashboard_context(user):
    branch = _branch_filter(user)
    branch_filter = {"branch": branch} if branch else {}
    customer_branch_filter = {"assigned_branch": branch} if branch else {}
    return {
        "branch": branch,
        "metrics": {
            "vehicles_available": Vehicle.objects.filter(status=Vehicle.Status.AVAILABLE, is_deleted=False, **branch_filter).count(),
            "vehicles_reserved": Vehicle.objects.filter(status=Vehicle.Status.RESERVED, is_deleted=False, **branch_filter).count(),
            "customers": Customer.objects.filter(is_deleted=False, **customer_branch_filter).count(),
            "sales_open": SaleRecord.objects.filter(is_deleted=False, **branch_filter).exclude(status__in=[SaleRecord.Status.SOLD, SaleRecord.Status.CANCELLED, SaleRecord.Status.VOID, SaleRecord.Status.EXPIRED]).count(),
            "low_stock": BranchStock.objects.filter(**branch_filter, minimum_stock__gt=0, quantity__lte=F("minimum_stock")).count(),
        },
        "recent_sales": SaleRecord.objects.filter(is_deleted=False, **branch_filter).select_related("customer", "vehicle", "vehicle__brand", "vehicle__model", "vehicle__model__brand")[:6],
        "recent_customers": Customer.objects.filter(is_deleted=False, **customer_branch_filter).select_related("assigned_branch", "assigned_advisor")[:6],
    }


def commercial_dashboard_context(user):
    qs = SaleRecord.objects.filter(is_deleted=False)
    leads = scoped_lead_queryset(user)
    total_leads = leads.count()
    won_leads = leads.filter(status=Lead.Status.WON).count()
    return {
        "metrics": {
            "quotes": qs.filter(status=SaleRecord.Status.QUOTED).count(),
            "reservations": qs.filter(status=SaleRecord.Status.RESERVED).count(),
            "sold": qs.filter(status=SaleRecord.Status.SOLD).count(),
            "prospects": Customer.objects.filter(status=Customer.Status.PROSPECT, is_deleted=False).count(),
            "leads_open": leads.exclude(status__in=[Lead.Status.WON, Lead.Status.LOST]).count(),
            "leads_won": won_leads,
            "lead_conversion": round(won_leads / total_leads * 100, 1) if total_leads else 0,
            "followups_overdue": leads.exclude(status__in=[Lead.Status.WON, Lead.Status.LOST]).filter(next_follow_up_at__lt=timezone.now()).count(),
            "total_pipeline": qs.exclude(status__in=[SaleRecord.Status.CANCELLED, SaleRecord.Status.VOID, SaleRecord.Status.EXPIRED]).aggregate(total=Sum("total"))["total"] or 0,
        },
        "attention_sales": qs.exclude(status__in=[SaleRecord.Status.SOLD, SaleRecord.Status.CANCELLED, SaleRecord.Status.VOID, SaleRecord.Status.EXPIRED]).select_related("customer", "branch", "vehicle", "vehicle__brand", "vehicle__model", "vehicle__model__brand")[:8],
        "latest_interests": CustomerVehicleInterest.objects.select_related("customer", "vehicle")[:6],
        "recent_leads": leads[:8],
    }


def seller_dashboard_context(user):
    qs = SaleRecord.objects.filter(is_deleted=False)
    if not getattr(user, "is_superuser", False):
        qs = qs.filter(advisor=user) | qs.filter(created_by=user)
    qs = qs.distinct().select_related("customer", "branch", "vehicle", "vehicle__brand", "vehicle__model", "vehicle__model__brand")
    leads = scoped_lead_queryset(user)
    return {
        "metrics": {
            "quotes": qs.filter(status=SaleRecord.Status.QUOTED).count(),
            "reservations": qs.filter(status=SaleRecord.Status.RESERVED).count(),
            "sold": qs.filter(status=SaleRecord.Status.SOLD).count(),
            "customers": Customer.objects.filter(is_deleted=False, assigned_advisor=user).count(),
            "leads_open": leads.exclude(status__in=[Lead.Status.WON, Lead.Status.LOST]).count(),
            "followups_overdue": leads.exclude(status__in=[Lead.Status.WON, Lead.Status.LOST]).filter(next_follow_up_at__lt=timezone.now()).count(),
        },
        "my_sales": qs[:8],
        "my_leads": leads[:8],
        "recent_customers": Customer.objects.filter(is_deleted=False).select_related("assigned_branch", "assigned_advisor")[:6],
    }


def inventory_dashboard_context(user):
    branch = _branch_filter(user)
    branch_filter = {"branch": branch} if branch else {}
    low_stock_qs = BranchStock.objects.filter(minimum_stock__gt=0, quantity__lte=F("minimum_stock"), **branch_filter).select_related("item", "branch")
    return {
        "branch": branch,
        "metrics": {
            "items": InventoryItem.objects.filter(is_deleted=False).count(),
            "low_stock": low_stock_qs.count(),
            "movements": StockMovement.objects.filter(**branch_filter).count(),
            "public_items": InventoryItem.objects.filter(is_deleted=False, is_public=True).count(),
        },
        "low_stock_records": low_stock_qs[:8],
        "recent_movements": StockMovement.objects.filter(**branch_filter).select_related("item", "branch", "destination_branch")[:8],
    }


def billing_dashboard_context(user):
    payable_statuses = [SaleRecord.Status.SOLD, SaleRecord.Status.APPROVED, SaleRecord.Status.RESERVED]
    sales_qs = SaleRecord.objects.filter(is_deleted=False, status__in=payable_statuses).select_related("customer", "branch", "vehicle", "vehicle__brand", "vehicle__model", "vehicle__model__brand")
    invoice_qs = InvoiceRecord.objects.filter(is_deleted=False).select_related("customer", "branch", "sale")
    return {
        "metrics": {
            "ready_sales": sales_qs.exclude(invoices__status__in=[InvoiceRecord.Status.DRAFT, InvoiceRecord.Status.ISSUED, InvoiceRecord.Status.PARTIAL, InvoiceRecord.Status.PAID]).distinct().count(),
            "confirmed_payments": SalePayment.objects.filter(status=SalePayment.Status.CONFIRMED).count(),
            "invoices_draft": invoice_qs.filter(status=InvoiceRecord.Status.DRAFT).count(),
            "invoices_issued": invoice_qs.filter(status__in=[InvoiceRecord.Status.ISSUED, InvoiceRecord.Status.PARTIAL]).count(),
            "private_documents": PrivateDocument.objects.filter(is_deleted=False).count(),
            "pending_documents": PrivateDocument.objects.filter(status=PrivateDocument.Status.PENDING_REVIEW, is_deleted=False).count(),
        },
        "ready_sales": sales_qs.exclude(invoices__status__in=[InvoiceRecord.Status.DRAFT, InvoiceRecord.Status.ISSUED, InvoiceRecord.Status.PARTIAL, InvoiceRecord.Status.PAID]).distinct()[:8],
        "recent_invoices": invoice_qs[:8],
        "recent_documents": PrivateDocument.objects.filter(is_deleted=False).select_related("customer", "sale")[:6],
    }


def support_dashboard_context(user):
    unread_qs = NotificationRecipient.objects.filter(user=user, status=NotificationRecipient.DeliveryStatus.UNREAD)
    return {
        "metrics": {
            "customers": Customer.objects.filter(is_deleted=False).count(),
            "important_notes": CustomerNote.objects.filter(is_important=True).count(),
            "open_interests": CustomerVehicleInterest.objects.filter(status=CustomerVehicleInterest.InterestStatus.OPEN).count(),
            "unread_notifications": unread_qs.count(),
            "new_leads": scoped_lead_queryset(user).filter(status=Lead.Status.NEW).count() if user.can_view_leads else 0,
        },
        "recent_customers": Customer.objects.filter(is_deleted=False).select_related("assigned_branch", "assigned_advisor")[:8],
        "unread_notifications": unread_qs.select_related("notification")[:6],
    }


def marketing_dashboard_context(user):
    vehicle_qs = Vehicle.objects.filter(is_deleted=False)
    return {
        "metrics": {
            "published": vehicle_qs.filter(is_public=True).count() if hasattr(Vehicle, "is_public") else public_vehicle_queryset().count(),
            "featured": vehicle_qs.filter(is_featured=True).count(),
            "available": vehicle_qs.filter(status=Vehicle.Status.AVAILABLE).count(),
            "assets": ReusableAsset.objects.filter(is_deleted=False).count(),
            "web_leads": Lead.objects.filter(is_deleted=False, source__in=[Lead.Source.WEB_CATALOG, Lead.Source.WEBSITE]).count(),
            "interactions": VehicleInteraction.objects.count(),
        },
        "featured_vehicles": vehicle_qs.filter(is_featured=True).select_related("brand", "model", "model__brand", "branch")[:8],
        "recent_assets": ReusableAsset.objects.filter(is_deleted=False).select_related("branch")[:6],
    }


def auditor_dashboard_context(user):
    audit_qs = scoped_audit_queryset(user)
    alert_qs = scoped_alert_queryset(user)
    return {
        "metrics": {
            "vehicles": Vehicle.objects.filter(is_deleted=False).count(),
            "customers": Customer.objects.filter(is_deleted=False).count(),
            "sales": SaleRecord.objects.filter(is_deleted=False).count(),
            "documents": PrivateDocument.objects.filter(is_deleted=False).count(),
            "audit_events": audit_qs.count(),
            "open_alerts": alert_qs.filter(status__in=[SecurityAlert.Status.OPEN, SecurityAlert.Status.IN_REVIEW]).count(),
            "leads": scoped_lead_queryset(user).count() if user.can_view_leads else 0,
            "interactions": VehicleInteraction.objects.count() if user.can_view_analytics else 0,
        },
        "recent_sales": SaleRecord.objects.filter(is_deleted=False).select_related("customer", "branch", "vehicle", "vehicle__brand", "vehicle__model", "vehicle__model__brand")[:8],
        "recent_documents": PrivateDocument.objects.filter(is_deleted=False).select_related("customer", "sale")[:8],
        "recent_audit_logs": audit_qs[:8],
        "recent_security_alerts": alert_qs[:6],
    }


def worker_dashboard_context(user):
    return {
        "metrics": dashboard_metrics(),
        "available_modules": [
            {"label": "Vehículos", "url": "vehicles_internal:list", "visible": user.can_view_internal_vehicles},
            {"label": "Clientes", "url": "customers_internal:list", "visible": user.can_view_customers},
            {"label": "Inventario", "url": "inventory_internal:list", "visible": user.can_view_inventory},
            {"label": "Ventas", "url": "sales_internal:list", "visible": user.can_access_sales},
            {"label": "CRM y leads", "url": "leads_internal:list", "visible": user.can_view_leads},
            {"label": "Analítica comercial", "url": "analytics_internal:home", "visible": user.can_view_analytics},
            {"label": "Documentos", "url": "documents_internal:list", "visible": user.can_view_documents},
            {"label": "Notificaciones", "url": "notifications_internal:inbox", "visible": user.can_view_notifications},
        ],
    }


def _metric(label, value, *, tone="primary", hint=""):
    return {"label": label, "value": value, "tone": tone, "hint": hint}


def _adaptive_metric_widget(key, user):
    """Build one authorized KPI block from canonical scoped selectors."""

    if key == "sales":
        month_start = timezone.localdate().replace(day=1)
        values = accessible_sales_queryset(user).aggregate(
            open=Count(
                "id",
                filter=Q(status__in=[
                    SaleRecord.Status.DRAFT,
                    SaleRecord.Status.QUOTED,
                    SaleRecord.Status.RESERVED,
                    SaleRecord.Status.APPROVED,
                ]),
            ),
            reserved=Count("id", filter=Q(status=SaleRecord.Status.RESERVED)),
            sold_month=Count(
                "id",
                filter=Q(status=SaleRecord.Status.SOLD, closed_at__date__gte=month_start),
            ),
            revenue_month=Sum(
                "total",
                filter=Q(status=SaleRecord.Status.SOLD, closed_at__date__gte=month_start),
            ),
        )
        values["revenue_month"] = values["revenue_month"] or 0
        return [
            _metric("Operaciones abiertas", values["open"], hint="Cotizadas, reservadas o aprobadas"),
            _metric("Reservas", values["reserved"], tone="warning", hint="Dentro de tu alcance"),
            _metric("Ventas del mes", values["sold_month"], tone="success"),
            _metric("Ingresos del mes", values["revenue_month"], tone="success", hint="Ventas confirmadas"),
        ], values
    if key == "leads":
        terminal = [Lead.Status.WON, Lead.Status.LOST]
        values = scoped_lead_queryset(user).aggregate(
            open=Count("id", filter=~Q(status__in=terminal)),
            new=Count("id", filter=Q(status=Lead.Status.NEW)),
            overdue=Count(
                "id",
                filter=Q(next_follow_up_at__lt=timezone.now()) & ~Q(status__in=terminal),
            ),
            won=Count("id", filter=Q(status=Lead.Status.WON)),
        )
        return [
            _metric("Leads abiertos", values["open"]),
            _metric("Nuevos", values["new"], tone="info"),
            _metric("Seguimientos vencidos", values["overdue"], tone="warning"),
            _metric("Convertidos", values["won"], tone="success"),
        ], values
    if key == "inventory":
        item_values = InventoryItem.objects.filter(is_deleted=False).aggregate(
            active_items=Count("id", filter=Q(status=InventoryItem.Status.ACTIVE)),
        )
        stock_qs = BranchStock.objects.filter(
            item__is_deleted=False,
            item__track_stock=True,
        )
        branch_ids = accessible_branch_ids(
            user,
            permission_codes=("inventory.view", "inventory.manage_stock"),
        )
        if branch_ids is not None:
            stock_qs = stock_qs.filter(branch_id__in=branch_ids)
        stock_values = stock_qs.aggregate(
            total_stock=Sum("quantity"),
            low_stock=Count("id", filter=Q(minimum_stock__gt=0, quantity__lte=F("minimum_stock"))),
            branches_with_stock=Count("branch_id", distinct=True),
        )
        values = {**item_values, **stock_values}
        values["total_stock"] = values["total_stock"] or 0
        return [
            _metric("Artículos activos", values["active_items"]),
            _metric("Stock total", values["total_stock"], tone="info"),
            _metric("Stock bajo", values["low_stock"], tone="warning"),
            _metric("Sucursales con stock", values["branches_with_stock"]),
        ], values
    if key == "invoices":
        month_start = timezone.localdate().replace(day=1)
        values = accessible_invoices_queryset(user).aggregate(
            draft=Count("id", filter=Q(status=InvoiceRecord.Status.DRAFT)),
            issued=Count("id", filter=Q(status=InvoiceRecord.Status.ISSUED)),
            paid=Count("id", filter=Q(status=InvoiceRecord.Status.PAID)),
            month_total=Sum("total", filter=Q(issue_date__gte=month_start)),
        )
        values["month_total"] = values["month_total"] or 0
        return [
            _metric("Borradores", values["draft"], tone="warning"),
            _metric("Emitidas", values["issued"], tone="info"),
            _metric("Pagadas", values["paid"], tone="success"),
            _metric("Facturado este mes", values["month_total"], tone="success"),
        ], values
    if key == "customers":
        values = accessible_customer_queryset(user).aggregate(
            total=Count("id"),
            prospect=Count("id", filter=Q(status=Customer.Status.PROSPECT)),
            active=Count("id", filter=Q(status__in=[Customer.Status.ACTIVE, Customer.Status.VIP])),
            with_branch=Count("id", filter=Q(assigned_branch__isnull=False)),
        )
        return [
            _metric("Clientes", values["total"]),
            _metric("Prospectos", values["prospect"], tone="info"),
            _metric("Activos", values["active"], tone="success"),
            _metric("Con sucursal", values["with_branch"]),
        ], values
    return [], {}


def _adaptive_tasks(user, widget_keys, metric_values, permission_codes):
    tasks = []
    if "sales" in widget_keys:
        count = sales_needing_attention_queryset(user).count()
        if count:
            tasks.append({
                "title": "Operaciones comerciales vencidas",
                "count": count,
                "url": reverse("sales_internal:attention"),
                "tone": "warning",
            })
    if "leads" in widget_keys:
        count = metric_values.get("leads", {}).get("overdue", 0)
        if count:
            tasks.append({
                "title": "Seguimientos de leads vencidos",
                "count": count,
                "url": f'{reverse("leads_internal:list")}?overdue=on',
                "tone": "warning",
            })
    if "inventory" in widget_keys:
        count = metric_values.get("inventory", {}).get("low_stock", 0)
        if count:
            tasks.append({
                "title": "Artículos con stock bajo",
                "count": count,
                "url": reverse("inventory_internal:low_stock"),
                "tone": "danger",
            })
    if "invoices" in widget_keys:
        count = metric_values.get("invoices", {}).get("draft", 0)
        if count:
            tasks.append({
                "title": "Comprobantes en borrador",
                "count": count,
                "url": f'{reverse("invoices_internal:list")}?status={InvoiceRecord.Status.DRAFT}',
                "tone": "info",
            })
    if {"notifications.view", "notifications.send"}.intersection(permission_codes) or user.is_superuser:
        count = NotificationRecipient.objects.filter(
            user=user,
            status=NotificationRecipient.DeliveryStatus.UNREAD,
        ).count()
        if count:
            tasks.append({
                "title": "Notificaciones sin leer",
                "count": count,
                "url": reverse("notifications_internal:inbox"),
                "tone": "primary",
            })
    return tasks[:6]


def _adaptive_activity(user, widget_keys, permission_codes):
    activity = []
    if "sales" in widget_keys:
        for sale in accessible_sales_queryset(user).select_related("customer").order_by("-updated_at")[:4]:
            activity.append({
                "kind": "Venta",
                "title": sale.number,
                "detail": sale.customer.display_name,
                "at": sale.updated_at,
                "url": reverse("sales_internal:detail", args=(sale.pk,)),
            })
    if "leads" in widget_keys:
        for lead in scoped_lead_queryset(user).order_by("-updated_at")[:4]:
            activity.append({
                "kind": "Lead",
                "title": lead.full_name,
                "detail": lead.get_status_display(),
                "at": lead.updated_at,
                "url": reverse("leads_internal:detail", args=(lead.pk,)),
            })
    if "inventory" in widget_keys:
        for movement in stock_movements_queryset(user=user)[:4]:
            activity.append({
                "kind": "Inventario",
                "title": movement.item.name,
                "detail": movement.get_movement_type_display(),
                "at": movement.updated_at,
                "url": reverse("inventory_internal:movement_list"),
            })
    if "invoices" in widget_keys:
        for invoice in accessible_invoices_queryset(user).order_by("-updated_at")[:4]:
            activity.append({
                "kind": "Factura",
                "title": invoice.number or "Borrador",
                "detail": invoice.get_status_display(),
                "at": invoice.updated_at,
                "url": reverse("invoices_internal:detail", args=(invoice.pk,)),
            })
    if "activity" in widget_keys and (
        {"documents.view", "documents.manage", "documents.download_private"}.intersection(permission_codes)
        or user.is_superuser
    ):
        for document in private_documents_queryset(user=user)[:4]:
            activity.append({
                "kind": "Documento",
                "title": document.title,
                "detail": document.get_status_display(),
                "at": document.updated_at,
                "url": reverse("documents_internal:detail", args=(document.pk,)),
            })
    activity.sort(key=lambda item: item["at"], reverse=True)
    return activity[:8]


def adaptive_dashboard_context(user, manifest):
    """Return one shared dashboard payload, limited to manifest-authorized data."""

    widget_keys = {widget.key for widget in manifest.widgets}
    widgets = []
    metric_values = {}
    metric_items = {}
    for definition in manifest.widgets:
        if definition.key in {"sales", "leads", "inventory", "invoices", "customers"}:
            items, values = _adaptive_metric_widget(definition.key, user)
            metric_items[definition.key] = items
            metric_values[definition.key] = values
    for definition in manifest.widgets:
        if definition.key in {"sales", "leads", "inventory", "invoices", "customers"}:
            widgets.append({
                "key": definition.key,
                "title": definition.title,
                "description": definition.description,
                "kind": "metrics",
                "items": metric_items[definition.key],
            })
        elif definition.key == "tasks":
            widgets.append({
                "key": definition.key,
                "title": definition.title,
                "description": definition.description,
                "kind": "tasks",
                "items": _adaptive_tasks(user, widget_keys, metric_values, manifest.permission_codes),
            })
        elif definition.key == "activity":
            widgets.append({
                "key": definition.key,
                "title": definition.title,
                "description": definition.description,
                "kind": "activity",
                "items": _adaptive_activity(user, widget_keys, manifest.permission_codes),
            })
    primary_widget = next((widget for widget in widgets if widget["kind"] == "metrics"), None)
    return {
        "dashboard_manifest": manifest,
        "dashboard_widgets": widgets,
        "dashboard_actions": manifest.actions,
        "dashboard_primary_widget": primary_widget,
        "dashboard_secondary_widgets": [
            widget
            for widget in widgets
            if widget["kind"] == "metrics" and widget is not primary_widget
        ],
        "dashboard_tasks_widget": next(
            (widget for widget in widgets if widget["kind"] == "tasks"),
            None,
        ),
        "dashboard_activity_widget": next(
            (widget for widget in widgets if widget["kind"] == "activity"),
            None,
        ),
    }
