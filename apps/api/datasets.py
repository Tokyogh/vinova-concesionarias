"""ES: Este módulo implementa el componente datasets para el dominio de API e integraciones.

EN: This module implements the datasets component for the api domain.

Contexto existente / Existing context:
Datasets support for the api domain.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db.models import F, Value
from django.db.models.functions import Greatest
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.exceptions import ValidationError

from apps.accounts.scopes import accessible_branch_ids
from apps.customers.models import Customer
from apps.inventory.models import BranchStock
from apps.invoices.models import InvoiceRecord
from apps.leads.models import Lead
from apps.sales.models import SaleRecord
from apps.vehicles.models import Vehicle

DATASET_VERSION = "1.0"
MAX_DATASET_LIMIT = 5000
DEFAULT_DATASET_LIMIT = 1000
SUPPORTED_DATASETS = ("sales", "invoices", "inventory", "customers", "leads", "vehicles")

DATASET_BRANCH_LOOKUPS = {
    "sales": "branch_id",
    "invoices": "branch_id",
    "inventory": "branch_id",
    "customers": "assigned_branch_id",
    "leads": "branch_id",
    "vehicles": "branch_id",
}


@dataclass(frozen=True)
class DatasetWindow:
    start: object | None
    end: object | None
    updated_since: object | None
    limit: int
    offset: int


def _positive_integer(raw: str, *, name: str, default: int, maximum: int | None = None) -> int:
    if raw in (None, ""):
        value = default
    else:
        try:
            value = int(raw)
        except (TypeError, ValueError) as exc:
            raise ValidationError({name: "Debe ser un número entero."}) from exc
    if value < 0 or (name == "limit" and value == 0):
        raise ValidationError({name: "Debe ser mayor que cero." if name == "limit" else "No puede ser negativo."})
    return min(value, maximum) if maximum is not None else value


def _window(request) -> DatasetWindow:
    start_raw = request.query_params.get("start_date", "")
    end_raw = request.query_params.get("end_date", "")
    updated_raw = request.query_params.get("updated_since", "")
    start = parse_date(start_raw) if start_raw else None
    end = parse_date(end_raw) if end_raw else None
    updated_since = parse_datetime(updated_raw) if updated_raw else None
    if start_raw and start is None:
        raise ValidationError({"start_date": "Usa el formato YYYY-MM-DD."})
    if end_raw and end is None:
        raise ValidationError({"end_date": "Usa el formato YYYY-MM-DD."})
    if updated_raw and updated_since is None:
        raise ValidationError({"updated_since": "Usa una fecha y hora ISO 8601."})
    if start and end and end < start:
        raise ValidationError({"end_date": "No puede ser anterior a start_date."})
    if updated_since and timezone.is_naive(updated_since):
        updated_since = timezone.make_aware(updated_since, timezone.get_current_timezone())
    return DatasetWindow(
        start=start,
        end=end,
        updated_since=updated_since,
        limit=_positive_integer(
            request.query_params.get("limit"),
            name="limit",
            default=DEFAULT_DATASET_LIMIT,
            maximum=MAX_DATASET_LIMIT,
        ),
        offset=_positive_integer(request.query_params.get("offset"), name="offset", default=0),
    )


def _branch_id(request):
    client = getattr(request, "api_client", None)
    return client.branch_id if client and client.branch_id else request.query_params.get("branch")


def _apply_user_branch_scope(queryset, request, name, permission_codes):
    branch_ids = accessible_branch_ids(request.user, permission_codes=permission_codes)
    if branch_ids is None:
        return queryset
    return queryset.filter(**{f"{DATASET_BRANCH_LOOKUPS[name]}__in": branch_ids})


def _apply_created_window(queryset, window: DatasetWindow, *, field: str = "created_at"):
    if window.start:
        queryset = queryset.filter(**{f"{field}__date__gte": window.start})
    if window.end:
        queryset = queryset.filter(**{f"{field}__date__lte": window.end})
    return queryset


def _apply_updated_since(queryset, window: DatasetWindow):
    if window.updated_since:
        return queryset.filter(updated_at__gte=window.updated_since)
    return queryset


def dataset_rows(name: str, request):
    """Build an authorized dataset using the request window and branch scope."""

    window = _window(request)
    branch_id = _branch_id(request)

    if name == "sales":
        queryset = SaleRecord.objects.filter(is_deleted=False).select_related("branch", "vehicle", "advisor")
        queryset = _apply_user_branch_scope(queryset, request, name, ("data.export", "analytics.export"))
        queryset = _apply_created_window(queryset, window)
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        queryset = _apply_updated_since(queryset, window)
        rows = queryset.order_by("id").values(
            "id",
            "number",
            "kind",
            "status",
            "source",
            "branch_id",
            "branch__code",
            "advisor_id",
            "vehicle_id",
            "vehicle__internal_code",
            "vehicle_price",
            "vehicle_discount",
            "subtotal",
            "tax_total",
            "total",
            "amount_paid",
            "balance_due",
            "valid_until",
            "reserved_until",
            "closed_at",
            "created_at",
            "updated_at",
        )
    elif name == "invoices":
        queryset = InvoiceRecord.objects.filter(is_deleted=False).select_related("branch", "company")
        queryset = _apply_user_branch_scope(queryset, request, name, ("data.export", "analytics.export"))
        if window.start:
            queryset = queryset.filter(issue_date__gte=window.start)
        if window.end:
            queryset = queryset.filter(issue_date__lte=window.end)
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        queryset = _apply_updated_since(queryset, window)
        rows = queryset.order_by("id").values(
            "id",
            "number",
            "invoice_type",
            "status",
            "sale_id",
            "company_id",
            "branch_id",
            "branch__code",
            "issue_date",
            "due_date",
            "currency",
            "subtotal",
            "discount_total",
            "tax_total",
            "total",
            "amount_paid",
            "balance_due",
            "issued_at",
            "voided_at",
            "created_at",
            "updated_at",
        )
    elif name == "inventory":
        queryset = BranchStock.objects.select_related("branch", "item", "item__category").annotate(
            available_quantity=Greatest(F("quantity") - F("reserved_quantity"), Value(0))
        )
        queryset = _apply_user_branch_scope(queryset, request, name, ("data.export", "analytics.export"))
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        queryset = _apply_updated_since(queryset, window)
        rows = queryset.order_by("id").values(
            "id",
            "branch_id",
            "branch__code",
            "item_id",
            "item__sku",
            "item__name",
            "item__item_type",
            "item__category__name",
            "quantity",
            "reserved_quantity",
            "available_quantity",
            "minimum_stock",
            "updated_at",
        )
    elif name == "customers":
        queryset = Customer.objects.filter(is_deleted=False)
        queryset = _apply_user_branch_scope(queryset, request, name, ("data.export", "analytics.export"))
        queryset = _apply_created_window(queryset, window)
        if branch_id:
            queryset = queryset.filter(assigned_branch_id=branch_id)
        queryset = _apply_updated_since(queryset, window)
        rows = queryset.order_by("id").values(
            "id",
            "customer_type",
            "status",
            "city",
            "province",
            "source",
            "assigned_branch_id",
            "assigned_advisor_id",
            "preferred_contact_method",
            "created_at",
            "updated_at",
        )
    elif name == "leads":
        queryset = Lead.objects.filter(is_deleted=False)
        queryset = _apply_user_branch_scope(queryset, request, name, ("data.export", "analytics.export"))
        queryset = _apply_created_window(queryset, window)
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        queryset = _apply_updated_since(queryset, window)
        rows = queryset.order_by("id").values(
            "id",
            "code",
            "request_type",
            "status",
            "priority",
            "source",
            "city",
            "province",
            "branch_id",
            "assigned_advisor_id",
            "vehicle_id",
            "interested_brand",
            "interested_model",
            "score",
            "closed_at",
            "created_at",
            "updated_at",
        )
    elif name == "vehicles":
        queryset = Vehicle.objects.filter(is_deleted=False).select_related("branch", "brand", "model")
        queryset = _apply_user_branch_scope(queryset, request, name, ("data.export", "analytics.export"))
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        queryset = _apply_updated_since(queryset, window)
        rows = queryset.order_by("id").values(
            "id",
            "internal_code",
            "brand__name",
            "model__name",
            "year",
            "version",
            "branch_id",
            "branch__code",
            "status",
            "price",
            "mileage",
            "is_featured",
            "published_at",
            "created_at",
            "updated_at",
        )
    else:
        raise KeyError(name)

    total = rows.count()
    result = list(rows[window.offset : window.offset + window.limit])
    columns = list(result[0].keys()) if result else list(rows.query.values_select)
    return {
        "dataset": name,
        "schema_version": DATASET_VERSION,
        "generated_at": timezone.now().isoformat(),
        "count": len(result),
        "total": total,
        "offset": window.offset,
        "limit": window.limit,
        "columns": columns,
        "results": result,
    }


def accounting_rows(request):
    window = _window(request)
    branch_id = _branch_id(request)
    queryset = (
        InvoiceRecord.objects.filter(is_deleted=False)
        .exclude(status=InvoiceRecord.Status.DRAFT)
        .select_related("branch", "company")
    )
    queryset = _apply_user_branch_scope(queryset, request, "invoices", ("data.export", "invoices.view"))
    if window.start:
        queryset = queryset.filter(issue_date__gte=window.start)
    if window.end:
        queryset = queryset.filter(issue_date__lte=window.end)
    if branch_id:
        queryset = queryset.filter(branch_id=branch_id)
    queryset = _apply_updated_since(queryset, window)
    values = queryset.order_by("issue_date", "number").values(
        "id",
        "number",
        "invoice_type",
        "status",
        "issue_date",
        "company__ruc",
        "branch__code",
        "customer_document",
        "currency",
        "subtotal",
        "discount_total",
        "tax_total",
        "total",
        "authorization_number",
        "access_key",
        "updated_at",
    )
    total = values.count()
    return list(values[window.offset : window.offset + window.limit]), total, window.offset, window.limit
