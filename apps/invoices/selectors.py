"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de facturación.

EN: This module implements authorization-aware read queries for the invoices domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the invoices domain.
"""

from __future__ import annotations

from django.db.models import Q, Sum
from django.utils import timezone

from apps.accounts.scopes import scope_queryset_to_user_branches
from apps.invoices.models import InvoiceRecord
from apps.sales.models import SaleRecord

INVOICE_SCOPE_PERMISSIONS = ("invoices.view", "invoices.issue", "invoices.manage")
INVOICE_ISSUE_PERMISSIONS = ("invoices.issue", "invoices.manage")
INVOICE_VOID_PERMISSIONS = ("invoices.void", "invoices.manage")


def accessible_invoices_queryset(user):
    return scope_queryset_to_user_branches(
        InvoiceRecord.objects.filter(is_deleted=False),
        user=user,
        permission_codes=INVOICE_SCOPE_PERMISSIONS,
        branch_lookup="branch",
    )


def invoice_list_queryset(user, *, query="", status="", invoice_type="", branch=None, sort=""):
    qs = accessible_invoices_queryset(user).select_related("company", "branch", "customer", "sale", "created_by", "issued_by")
    if query:
        qs = qs.filter(
            Q(number__icontains=query)
            | Q(customer_name__icontains=query)
            | Q(customer_document__icontains=query)
            | Q(customer_email__icontains=query)
            | Q(authorization_number__icontains=query)
            | Q(access_key__icontains=query)
            | Q(sale__number__icontains=query)
        )
    if status:
        qs = qs.filter(status=status)
    if invoice_type:
        qs = qs.filter(invoice_type=invoice_type)
    if branch:
        qs = qs.filter(branch=branch)
    ordering = {
        "oldest": ("created_at",), "total_desc": ("-total", "-created_at"),
        "due_asc": ("due_date", "-created_at"),
    }.get(sort, ("-created_at",))
    return qs.order_by(*ordering)


def invoice_detail_queryset(user):
    return accessible_invoices_queryset(user).select_related("company", "branch", "customer", "sale", "linked_document", "created_by", "issued_by", "voided_by").prefetch_related("lines", "payment_applications", "status_history")


def invoice_metrics(user):
    month_start = timezone.localdate().replace(day=1)
    active = accessible_invoices_queryset(user)
    return {
        "draft": active.filter(status=InvoiceRecord.Status.DRAFT).count(),
        "issued": active.filter(status=InvoiceRecord.Status.ISSUED).count(),
        "partial": active.filter(status=InvoiceRecord.Status.PARTIAL).count(),
        "paid": active.filter(status=InvoiceRecord.Status.PAID).count(),
        "month_total": active.filter(issue_date__gte=month_start).aggregate(total=Sum("total"))["total"] or 0,
    }


def ready_sales_for_invoicing_queryset(user):
    return (
        scope_queryset_to_user_branches(
            SaleRecord.objects.filter(is_deleted=False, status__in=[SaleRecord.Status.SOLD, SaleRecord.Status.APPROVED, SaleRecord.Status.RESERVED]),
            user=user,
            permission_codes=INVOICE_SCOPE_PERMISSIONS,
            branch_lookup="branch",
        )
        .select_related("customer", "branch", "vehicle", "vehicle__brand", "vehicle__model", "vehicle__model__brand", "advisor")
        .exclude(invoices__status__in=[InvoiceRecord.Status.DRAFT, InvoiceRecord.Status.ISSUED, InvoiceRecord.Status.PARTIAL, InvoiceRecord.Status.PAID])
        .distinct()
        .order_by("-updated_at")
    )


def invoice_payments_queryset(invoice: InvoiceRecord):
    return invoice.payment_applications.select_related("sale_payment", "applied_by")
