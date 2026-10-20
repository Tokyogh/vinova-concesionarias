"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de reportes.

EN: This module implements authorization-aware read queries for the reports domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the reports domain.
"""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.accounts.scopes import (
    accessible_branch_ids,
    accessible_branches_queryset,
    accessible_users_queryset,
    scope_queryset_to_user_branches,
)
from apps.audit.models import AuditLog
from apps.customers.models import Customer
from apps.documents.models import PrivateDocument
from apps.inventory.models import BranchStock, InventoryItem, StockMovement
from apps.invoices.models import InvoiceRecord
from apps.sales.models import SaleLine, SalePayment, SaleRecord
from apps.vehicles.models import Vehicle


REPORT_PERMISSION_CODES = ("reports.view",)


def _zero(value):
    return value if value is not None else Decimal("0.00")


def filters_from_form(form):
    data = getattr(form, "cleaned_data", {}) or {}
    today = timezone.localdate()
    start = data.get("start_date") or today.replace(day=1)
    end = data.get("end_date") or today
    return {
        "start_date": start,
        "end_date": end,
        "branch": data.get("branch"),
        "seller": data.get("seller"),
        "sale_status": data.get("sale_status", ""),
        "vehicle": data.get("vehicle"),
        "category": data.get("category"),
        "q": (data.get("q") or "").strip(),
    }


def filters_as_json(filters):
    return {
        "start_date": filters["start_date"].isoformat(),
        "end_date": filters["end_date"].isoformat(),
        "branch_id": filters["branch"].pk if filters.get("branch") else None,
        "seller_id": filters["seller"].pk if filters.get("seller") else None,
        "sale_status": filters.get("sale_status", ""),
        "vehicle_id": filters["vehicle"].pk if filters.get("vehicle") else None,
        "category_id": filters["category"].pk if filters.get("category") else None,
        "q": filters.get("q", ""),
    }


def branch_limited_queryset(qs, user, field_name="branch"):
    return scope_queryset_to_user_branches(
        qs,
        user=user,
        permission_codes=REPORT_PERMISSION_CODES,
        branch_lookup=field_name,
    )


def apply_date_range(qs, filters, field="created_at"):
    return qs.filter(**{f"{field}__date__gte": filters["start_date"], f"{field}__date__lte": filters["end_date"]})


def apply_branch_filter(qs, filters, field="branch"):
    branch = filters.get("branch")
    if branch:
        return qs.filter(**{field: branch})
    return qs


def apply_sale_dimensions(qs, filters, prefix=""):
    if filters.get("seller"):
        qs = qs.filter(**{f"{prefix}advisor": filters["seller"]})
    if filters.get("sale_status"):
        qs = qs.filter(**{f"{prefix}status": filters["sale_status"]})
    if filters.get("vehicle"):
        qs = qs.filter(**{f"{prefix}vehicle": filters["vehicle"]})
    if filters.get("category"):
        qs = qs.filter(**{f"{prefix}lines__item__category": filters["category"]})
    return qs.distinct()


def executive_context(filters, user):
    """ES: Ejecuta la operación «executive context» dentro del dominio de reportes.

    EN: Executes the «executive context» operation within the reports domain.
    """

    sales = branch_limited_queryset(SaleRecord.objects.all(), user)
    sales = apply_branch_filter(apply_date_range(sales, filters), filters)
    sales = apply_sale_dimensions(sales, filters)
    invoices = branch_limited_queryset(InvoiceRecord.objects.all(), user)
    invoices = apply_branch_filter(invoices.filter(issue_date__gte=filters["start_date"], issue_date__lte=filters["end_date"]), filters)
    invoices = apply_sale_dimensions(invoices, filters, "sale__")
    vehicles = branch_limited_queryset(Vehicle.objects.all(), user)
    vehicles = apply_branch_filter(vehicles, filters)
    customers = branch_limited_queryset(Customer.objects.all(), user, "assigned_branch")
    if filters.get("branch"):
        customers = customers.filter(assigned_branch=filters["branch"])

    payments = branch_limited_queryset(
        SalePayment.objects.filter(status=SalePayment.Status.CONFIRMED),
        user,
        "sale__branch",
    )
    payments = apply_date_range(payments, filters, "paid_at")
    payments = apply_branch_filter(payments, filters, "sale__branch")
    payments = apply_sale_dimensions(payments, filters, "sale__")
    documents = branch_limited_queryset(
        PrivateDocument.objects.filter(is_deleted=False),
        user,
    )
    documents = apply_branch_filter(documents, filters)

    sales_metrics = sales.aggregate(
        operations_count=Count("id"),
        sales_count=Count("id", filter=Q(status=SaleRecord.Status.SOLD)),
        sales_total=Sum("total", filter=Q(status=SaleRecord.Status.SOLD)),
        cancelled_sales=Count(
            "id",
            filter=Q(status__in=(SaleRecord.Status.CANCELLED, SaleRecord.Status.VOID)),
        ),
        reservations=Count("id", filter=Q(status=SaleRecord.Status.RESERVED)),
        pending_balance=Sum(
            "balance_due",
            filter=Q(
                status__in=(SaleRecord.Status.RESERVED, SaleRecord.Status.APPROVED, SaleRecord.Status.SOLD),
                balance_due__gt=0,
            ),
        ),
    )
    invoice_metrics = invoices.exclude(
        status__in=(InvoiceRecord.Status.DRAFT, InvoiceRecord.Status.VOID, InvoiceRecord.Status.CANCELLED)
    ).aggregate(count=Count("id"), total=Sum("total"))
    vehicle_metrics = vehicles.aggregate(
        available=Count("id", filter=Q(status=Vehicle.Status.AVAILABLE)),
        reserved=Count("id", filter=Q(status=Vehicle.Status.RESERVED)),
        sold=Count("id", filter=Q(status=Vehicle.Status.SOLD)),
    )

    return {
        "metrics": {
            "operations_count": sales_metrics["operations_count"],
            "sales_count": sales_metrics["sales_count"],
            "sales_total": _zero(sales_metrics["sales_total"]),
            "cancelled_sales": sales_metrics["cancelled_sales"],
            "reservations": sales_metrics["reservations"],
            "payments_total": _zero(payments.aggregate(total=Sum("amount"))["total"]),
            "pending_balance": _zero(sales_metrics["pending_balance"]),
            "invoices_count": invoice_metrics["count"],
            "invoices_total": _zero(invoice_metrics["total"]),
            "available_vehicles": vehicle_metrics["available"],
            "reserved_vehicles": vehicle_metrics["reserved"],
            "sold_vehicles": vehicle_metrics["sold"],
            "new_customers": apply_date_range(customers, filters).count(),
            "low_stock": low_stock_queryset(filters, user).count(),
            "pending_documents": documents.filter(status=PrivateDocument.Status.PENDING_REVIEW).count(),
        },
        "sales_by_status": list(sales.values("status").annotate(count=Count("id"), total=Sum("total")).order_by("status")),
        "invoices_by_status": list(invoices.values("status").annotate(count=Count("id"), total=Sum("total")).order_by("status")),
        "branch_summary": branch_summary(filters, user)[:6],
        "seller_summary": seller_summary(filters, user)[:8],
        "recent_sales": sales.select_related("customer", "branch", "advisor").order_by("-created_at")[:8],
        "recent_invoices": invoices.select_related("customer", "branch").order_by("-issue_date", "-created_at")[:8],
    }


def sales_queryset(filters, user):
    qs = SaleRecord.objects.select_related("customer", "branch", "advisor", "vehicle", "vehicle__brand", "vehicle__model", "vehicle__model__brand").order_by("-created_at")
    qs = branch_limited_queryset(qs, user)
    qs = apply_branch_filter(apply_date_range(qs, filters), filters)
    qs = apply_sale_dimensions(qs, filters)
    q = filters.get("q")
    if q:
        qs = qs.filter(
            Q(number__icontains=q)
            | Q(customer__first_name__icontains=q)
            | Q(customer__last_name__icontains=q)
            | Q(customer__business_name__icontains=q)
            | Q(customer__identification_number__icontains=q)
            | Q(vehicle__internal_code__icontains=q) | Q(vehicle__vin__icontains=q)
            | Q(vehicle__plate__icontains=q)
        )
    return qs


def sales_context(filters, user):
    qs = sales_queryset(filters, user)
    payments = SalePayment.objects.filter(sale__in=qs, status=SalePayment.Status.CONFIRMED)
    return {
        "metrics": {
            "count": qs.count(),
            "total": _zero(qs.aggregate(total=Sum("total"))["total"]),
            "paid": _zero(payments.aggregate(total=Sum("amount"))["total"]),
            "balance": _zero(qs.aggregate(total=Sum("balance_due"))["total"]),
        },
        "status_rows": list(qs.values("status").annotate(count=Count("id"), total=Sum("total")).order_by("status")),
        "date_rows": list(qs.annotate(day=TruncDate("created_at")).values("day").annotate(count=Count("id"), total=Sum("total")).order_by("-day")[:31]),
        "branch_rows": branch_summary(filters, user),
        "seller_rows": seller_summary(filters, user),
        "object_list": qs[:50],
    }


def branch_summary(filters, user):
    sales = sales_queryset(filters, user)
    return list(
        sales.values("branch__name", "branch__city")
        .annotate(count=Count("id"), total=Sum("total"))
        .order_by("-total", "branch__name")
    )


def seller_summary(filters, user):
    return list(
        sales_queryset(filters, user)
        .filter(status=SaleRecord.Status.SOLD, advisor__isnull=False)
        .values("advisor_id", "advisor__username", "advisor__first_name", "advisor__last_name")
        .annotate(count=Count("id"), total=Sum("total"), paid=Sum("amount_paid"), balance=Sum("balance_due"))
        .order_by("-total", "advisor__username")
    )


def vehicles_queryset(filters, user):
    qs = Vehicle.objects.select_related("brand", "model", "model__brand", "branch").order_by("brand__name", "model__name", "year")
    qs = branch_limited_queryset(qs, user)
    qs = apply_branch_filter(qs, filters)
    if filters.get("vehicle"):
        qs = qs.filter(pk=filters["vehicle"].pk)
    q = filters.get("q")
    if q:
        qs = qs.filter(
            Q(internal_code__icontains=q) | Q(vin__icontains=q)
            | Q(plate__icontains=q)
            | Q(brand__name__icontains=q)
            | Q(model__name__icontains=q)
            | Q(version__icontains=q)
            | Q(color__icontains=q)
        )
    return qs


def vehicles_context(filters, user):
    qs = vehicles_queryset(filters, user)
    return {
        "metrics": {
            "total": qs.count(),
            "available": qs.filter(status=Vehicle.Status.AVAILABLE).count(),
            "reserved": qs.filter(status=Vehicle.Status.RESERVED).count(),
            "sold": qs.filter(status=Vehicle.Status.SOLD).count(),
        },
        "status_rows": list(qs.values("status").annotate(count=Count("id"), value=Sum("price")).order_by("status")),
        "branch_rows": list(qs.values("branch__name", "branch__city").annotate(count=Count("id"), value=Sum("price")).order_by("-count")),
        "brand_rows": list(qs.values("brand__name").annotate(count=Count("id"), value=Sum("price")).order_by("-count")[:12]),
        "object_list": qs[:80],
    }


def low_stock_queryset(filters, user):
    qs = BranchStock.objects.select_related("item", "item__category", "branch").filter(
        item__track_stock=True,
        item__status=InventoryItem.Status.ACTIVE,
        minimum_stock__gt=0,
        quantity__lte=F("minimum_stock"),
    )
    qs = branch_limited_queryset(qs, user)
    qs = apply_branch_filter(qs, filters)
    if filters.get("category"):
        qs = qs.filter(item__category=filters["category"])
    q = filters.get("q")
    if q:
        qs = qs.filter(Q(item__sku__icontains=q) | Q(item__name__icontains=q) | Q(branch__name__icontains=q))
    return qs.order_by("quantity", "item__name")


def stock_movements_queryset(filters, user):
    qs = StockMovement.objects.select_related("item", "branch", "destination_branch", "created_by").order_by("-confirmed_at", "-created_at")
    branch_ids = accessible_branch_ids(user, permission_codes=REPORT_PERMISSION_CODES)
    if branch_ids is not None:
        if not branch_ids:
            qs = qs.none()
        else:
            qs = qs.filter(Q(branch_id__in=branch_ids) | Q(destination_branch_id__in=branch_ids))
    qs = apply_date_range(qs, filters)
    if filters.get("branch"):
        branch = filters["branch"]
        qs = qs.filter(Q(branch=branch) | Q(destination_branch=branch))
    if filters.get("category"):
        qs = qs.filter(item__category=filters["category"])
    q = filters.get("q")
    if q:
        qs = qs.filter(Q(item__sku__icontains=q) | Q(item__name__icontains=q) | Q(reference__icontains=q) | Q(reason__icontains=q))
    return qs


def inventory_context(filters, user):
    low = low_stock_queryset(filters, user)
    movements = stock_movements_queryset(filters, user)
    stock_scope = branch_limited_queryset(BranchStock.objects.select_related("item", "branch"), user)
    stock_scope = apply_branch_filter(stock_scope, filters)
    if filters.get("category"):
        stock_scope = stock_scope.filter(item__category=filters["category"])
    return {
        "metrics": {
            "low_stock": low.count(),
            "stock_records": stock_scope.count(),
            "stock_units": _zero(stock_scope.aggregate(total=Sum("quantity"))["total"]),
            "movements": movements.count(),
        },
        "low_stock_rows": low[:80],
        "movement_type_rows": list(movements.values("movement_type").annotate(count=Count("id"), quantity=Sum("quantity")).order_by("movement_type")),
        "recent_movements": movements[:60],
    }


def invoices_queryset(filters, user):
    qs = InvoiceRecord.objects.select_related("company", "branch", "customer", "sale").order_by("-issue_date", "-created_at")
    qs = branch_limited_queryset(qs, user)
    qs = apply_branch_filter(qs.filter(issue_date__gte=filters["start_date"], issue_date__lte=filters["end_date"]), filters)
    qs = apply_sale_dimensions(qs, filters, "sale__")
    q = filters.get("q")
    if q:
        qs = qs.filter(
            Q(number__icontains=q)
            | Q(customer_name__icontains=q)
            | Q(customer_document__icontains=q)
            | Q(authorization_number__icontains=q)
            | Q(access_key__icontains=q)
            | Q(external_reference__icontains=q)
        )
    return qs


def invoices_context(filters, user):
    qs = invoices_queryset(filters, user)
    return {
        "metrics": {
            "count": qs.count(),
            "total": _zero(qs.aggregate(total=Sum("total"))["total"]),
            "paid": _zero(qs.aggregate(total=Sum("amount_paid"))["total"]),
            "balance": _zero(qs.aggregate(total=Sum("balance_due"))["total"]),
        },
        "status_rows": list(qs.values("status").annotate(count=Count("id"), total=Sum("total")).order_by("status")),
        "type_rows": list(qs.values("invoice_type").annotate(count=Count("id"), total=Sum("total")).order_by("invoice_type")),
        "date_rows": list(qs.values("issue_date").annotate(count=Count("id"), total=Sum("total")).order_by("-issue_date")[:31]),
        "object_list": qs[:60],
    }


def customers_queryset(filters, user):
    qs = Customer.objects.select_related("assigned_branch", "assigned_advisor").order_by("-created_at")
    qs = branch_limited_queryset(qs, user, "assigned_branch")
    if filters.get("branch"):
        qs = qs.filter(assigned_branch=filters["branch"])
    if filters.get("seller"):
        qs = qs.filter(assigned_advisor=filters["seller"])
    qs = apply_date_range(qs, filters)
    q = filters.get("q")
    if q:
        qs = qs.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(business_name__icontains=q)
            | Q(email__icontains=q)
            | Q(phone__icontains=q)
            | Q(identification_number__icontains=q)
            | Q(city__icontains=q)
        )
    return qs


def customers_context(filters, user):
    qs = customers_queryset(filters, user)
    return {
        "metrics": {
            "count": qs.count(),
            "prospects": qs.filter(status=Customer.Status.PROSPECT).count(),
            "active": qs.filter(status=Customer.Status.ACTIVE).count(),
            "vip": qs.filter(status=Customer.Status.VIP).count(),
        },
        "status_rows": list(qs.values("status").annotate(count=Count("id")).order_by("status")),
        "city_rows": list(qs.values("city", "province").annotate(count=Count("id")).order_by("-count", "city")[:20]),
        "advisor_rows": list(qs.values("assigned_advisor__username", "assigned_advisor__first_name", "assigned_advisor__last_name").annotate(count=Count("id")).order_by("-count")[:20]),
        "object_list": qs[:80],
    }


def activity_queryset(filters, user):
    qs = AuditLog.objects.select_related("user", "branch").order_by("-created_at")
    qs = branch_limited_queryset(qs, user)
    qs = apply_branch_filter(qs, filters)
    qs = apply_date_range(qs, filters)
    q = filters.get("q")
    if q:
        qs = qs.filter(Q(action__icontains=q) | Q(object_repr__icontains=q) | Q(user__username__icontains=q) | Q(user__email__icontains=q))
    return qs


def activity_context(filters, user):
    qs = activity_queryset(filters, user)
    users = accessible_users_queryset(user, permission_codes=REPORT_PERMISSION_CODES).count()
    return {
        "metrics": {
            "events": qs.count(),
            "active_users": users,
            "critical": qs.filter(action__icontains="delete").count() + qs.filter(action__icontains="void").count(),
            "downloads": qs.filter(action__icontains="download").count(),
        },
        "action_rows": list(qs.values("action").annotate(count=Count("id")).order_by("-count")[:30]),
        "user_rows": list(qs.values("user__username", "user__email").annotate(count=Count("id")).order_by("-count")[:25]),
        "object_list": qs[:100],
    }


def products_context(filters, user):
    sales = sales_queryset(filters, user)
    lines = SaleLine.objects.select_related("item", "sale", "sale__branch").filter(sale__in=sales)
    q = filters.get("q")
    if q:
        lines = lines.filter(Q(description__icontains=q) | Q(item__sku__icontains=q) | Q(item__name__icontains=q))
    return {
        "metrics": {
            "lines": lines.count(),
            "quantity": _zero(lines.aggregate(total=Sum("quantity"))["total"]),
            "subtotal": _zero(lines.aggregate(total=Sum("line_subtotal"))["total"]),
            "total": _zero(lines.aggregate(total=Sum("line_total"))["total"]),
        },
        "product_rows": list(
            lines.values("item__sku", "item__name", "description")
            .annotate(quantity=Sum("quantity"), total=Sum("line_total"), count=Count("id"))
            .order_by("-total", "-quantity")[:50]
        ),
        "object_list": lines.order_by("-sale__created_at")[:80],
    }


def branches_context(filters, user):
    branches = accessible_branches_queryset(user, permission_codes=REPORT_PERMISSION_CODES)
    if filters.get("branch"):
        branches = branches.filter(pk=filters["branch"].pk)
    summaries = []
    for branch in branches:
        branch_filters = {**filters, "branch": branch}
        sales = sales_queryset(branch_filters, user)
        invoices = invoices_queryset(branch_filters, user)
        vehicles = vehicles_queryset(branch_filters, user)
        summaries.append(
            {
                "branch": branch,
                "sales_count": sales.count(),
                "sales_total": _zero(sales.aggregate(total=Sum("total"))["total"]),
                "invoices_count": invoices.count(),
                "invoices_total": _zero(invoices.aggregate(total=Sum("total"))["total"]),
                "available_vehicles": vehicles.filter(status=Vehicle.Status.AVAILABLE).count(),
                "low_stock": low_stock_queryset(branch_filters, user).count(),
            }
        )
    return {
        "metrics": {
            "branches": len(summaries),
            "sales_total": sum((x["sales_total"] for x in summaries), Decimal("0.00")),
            "invoices_total": sum((x["invoices_total"] for x in summaries), Decimal("0.00")),
            "low_stock": sum((x["low_stock"] for x in summaries), 0),
        },
        "branch_cards": summaries,
    }


def reports_home_context(filters, user):
    ctx = executive_context(filters, user)
    ctx["module_cards"] = [
        {"code": "sales", "title": "Ventas por fecha", "description": "Cotizaciones, reservas, ventas, pagos, saldos y comportamiento por día."},
        {"code": "branches", "title": "Ventas por sucursal", "description": "Comparativo operativo por sede: ventas, facturas, vehículos y stock bajo."},
        {"code": "vehicles", "title": "Vehículos por estado", "description": "Disponibles, reservados, vendidos, ocultos y valor aproximado del catálogo."},
        {"code": "inventory", "title": "Inventario bajo", "description": "Stock crítico, movimientos recientes y tipos de movimiento por sucursal."},
        {"code": "stock_movements", "title": "Movimientos de stock", "description": "Trazabilidad exportable de entradas, salidas, ajustes, ventas y transferencias."},
        {"code": "invoices", "title": "Facturas emitidas", "description": "Comprobantes, proformas, notas, pagos aplicados y saldos."},
        {"code": "customers", "title": "Clientes nuevos", "description": "Altas por fecha, estado, ciudad y asesor asignado."},
        {"code": "products", "title": "Productos más vendidos", "description": "Artículos, accesorios y servicios vendidos por cantidad e importe."},
        {"code": "activity", "title": "Actividad de usuarios", "description": "Eventos auditados, usuarios activos, descargas y acciones críticas."},
    ]
    return ctx
