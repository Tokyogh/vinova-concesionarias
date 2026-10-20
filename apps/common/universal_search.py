"""ES: Este módulo implementa el componente universal search para el dominio de infraestructura compartida.

EN: This module implements the universal search component for the common domain.

Contexto existente / Existing context:
Universal search support for the common domain.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from django.db.models import Q
from django.urls import reverse

from apps.common.capabilities import allows_capability, permission_codes_for_user
from apps.customers.selectors import accessible_customer_queryset
from apps.documents.selectors import private_documents_queryset
from apps.invoices.selectors import accessible_invoices_queryset
from apps.leads.selectors import scoped_lead_queryset
from apps.sales.selectors import accessible_sales_queryset
from apps.vehicles.selectors import accessible_vehicle_queryset


RESULTS_PER_SOURCE = 4
MAX_QUERY_LENGTH = 120


@dataclass(frozen=True)
class SearchSource:
    key: str
    capability: str
    search: Callable


def _branch_label(branch) -> str:
    return branch.name if branch else "Sin sucursal"


def _vehicle_results(user, query: str) -> list[dict]:
    records = (
        accessible_vehicle_queryset(user)
        .filter(
            Q(brand__name__icontains=query)
            | Q(model__name__icontains=query)
            | Q(version__icontains=query)
            | Q(internal_code__icontains=query)
            | Q(vin__icontains=query)
            | Q(plate__icontains=query)
        )
        .select_related("brand", "model", "model__brand", "branch")
        .order_by("-updated_at")[:RESULTS_PER_SOURCE]
    )
    return [
        {
            "key": f"entity:vehicle:{record.pk}",
            "title": str(record),
            "description": f"Vehículo · {record.internal_code} · {_branch_label(record.branch)}",
            "url": reverse("vehicles_internal:detail", args=[record.pk]),
            "kind": "entity",
            "area": "Vehículos",
            "keywords": [record.internal_code, record.vin or "", record.plate],
        }
        for record in records
    ]


def _customer_results(user, query: str) -> list[dict]:
    records = (
        accessible_customer_queryset(user)
        .filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(business_name__icontains=query)
            | Q(identification_number__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
        )
        .select_related("assigned_branch")
        .order_by("-updated_at")[:RESULTS_PER_SOURCE]
    )
    return [
        {
            "key": f"entity:customer:{record.pk}",
            "title": record.display_name,
            "description": f"Cliente · {record.identification_number or 'Sin identificación'} · {_branch_label(record.assigned_branch)}",
            "url": reverse("customers_internal:detail", args=[record.pk]),
            "kind": "entity",
            "area": "Clientes",
            "keywords": [record.identification_number or "", record.email, record.phone],
        }
        for record in records
    ]


def _lead_results(user, query: str) -> list[dict]:
    records = (
        scoped_lead_queryset(user)
        .prefetch_related(None)
        .filter(
            Q(code__icontains=query)
            | Q(full_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
            | Q(whatsapp__icontains=query)
            | Q(interested_brand__icontains=query)
            | Q(interested_model__icontains=query)
        )
        .order_by("-updated_at")[:RESULTS_PER_SOURCE]
    )
    return [
        {
            "key": f"entity:lead:{record.pk}",
            "title": record.full_name,
            "description": f"Lead · {record.code} · {record.get_status_display()}",
            "url": reverse("leads_internal:detail", args=[record.pk]),
            "kind": "entity",
            "area": "Leads",
            "keywords": [record.code, record.email, record.phone, record.whatsapp],
        }
        for record in records
    ]


def _sale_results(user, query: str) -> list[dict]:
    records = (
        accessible_sales_queryset(user)
        .filter(
            Q(number__icontains=query)
            | Q(customer__first_name__icontains=query)
            | Q(customer__last_name__icontains=query)
            | Q(customer__business_name__icontains=query)
            | Q(customer__identification_number__icontains=query)
            | Q(vehicle__internal_code__icontains=query)
            | Q(vehicle__vin__icontains=query)
            | Q(vehicle__plate__icontains=query)
        )
        .select_related("customer", "branch")
        .order_by("-updated_at")[:RESULTS_PER_SOURCE]
    )
    return [
        {
            "key": f"entity:sale:{record.pk}",
            "title": record.number,
            "description": f"Venta/cotización · {record.customer.display_name} · {record.get_status_display()}",
            "url": reverse("sales_internal:detail", args=[record.pk]),
            "kind": "entity",
            "area": "Ventas",
            "keywords": [record.number, record.customer.identification_number or ""],
        }
        for record in records
    ]


def _invoice_results(user, query: str) -> list[dict]:
    records = (
        accessible_invoices_queryset(user)
        .filter(
            Q(number__icontains=query)
            | Q(customer_name__icontains=query)
            | Q(customer_document__icontains=query)
            | Q(customer_email__icontains=query)
            | Q(authorization_number__icontains=query)
            | Q(access_key__icontains=query)
            | Q(sale__number__icontains=query)
        )
        .select_related("branch")
        .order_by("-updated_at")[:RESULTS_PER_SOURCE]
    )
    return [
        {
            "key": f"entity:invoice:{record.pk}",
            "title": record.number,
            "description": f"Factura · {record.customer_name} · {record.get_status_display()}",
            "url": reverse("invoices_internal:detail", args=[record.pk]),
            "kind": "entity",
            "area": "Facturas",
            "keywords": [record.number, record.customer_document],
        }
        for record in records
    ]


def _document_results(user, query: str) -> list[dict]:
    records = private_documents_queryset(user=user, query=query)[:RESULTS_PER_SOURCE]
    return [
        {
            "key": f"entity:document:{record.pk}",
            "title": record.title,
            "description": f"Documento · {record.get_document_type_display()} · {_branch_label(record.branch)}",
            "url": reverse("documents_internal:detail", args=[record.pk]),
            "kind": "entity",
            "area": "Documentos",
            "keywords": [record.original_name, record.get_document_type_display()],
        }
        for record in records
    ]


SEARCH_SOURCES = (
    SearchSource("vehicles", "can_view_internal_vehicles", _vehicle_results),
    SearchSource("customers", "can_view_customers", _customer_results),
    SearchSource("leads", "can_view_leads", _lead_results),
    SearchSource("sales", "can_access_sales", _sale_results),
    SearchSource("invoices", "can_view_invoices", _invoice_results),
    SearchSource("documents", "can_view_documents", _document_results),
)


def universal_search_for_user(user, query: str) -> dict:
    """Busca únicamente después de autorizar cada fuente y aplica su scope canónico."""
    query = " ".join((query or "").strip().split())[:MAX_QUERY_LENGTH]
    if len(query) < 2:
        return {"query": query, "count": 0, "results": []}

    permission_codes = permission_codes_for_user(user)
    results = []
    for source in SEARCH_SOURCES:
        if allows_capability(source.capability, user, permission_codes):
            results.extend(source.search(user, query))
    return {"query": query, "count": len(results), "results": results}
