"""ES: Este módulo implementa el componente filtering para el dominio de API e integraciones.

EN: This module implements the filtering component for the api domain.

Contexto existente / Existing context:
Filtering support for the api domain.
"""

from django.db.models import Q
from rest_framework.filters import BaseFilterBackend

from apps.accounts.scopes import users_in_branches_queryset


BRANCH_LOOKUPS = {
    "branches.branch": "pk",
    "vehicles.vehicle": "branch_id",
    "customers.customer": "assigned_branch_id",
    "customers.customernote": "customer__assigned_branch_id",
    "customers.customervehicleinterest": "customer__assigned_branch_id",
    "inventory.branchstock": "branch_id",
    "sales.salerecord": "branch_id",
    "sales.saleline": "sale__branch_id",
    "sales.salepayment": "sale__branch_id",
    "sales.salestatushistory": "sale__branch_id",
    "invoices.invoicerecord": "branch_id",
    "invoices.invoiceline": "invoice__branch_id",
    "invoices.invoicepaymentapplication": "invoice__branch_id",
    "invoices.invoicestatushistory": "invoice__branch_id",
    "leads.lead": "branch_id",
    "leads.leadactivity": "lead__branch_id",
    "leads.testdrive": "branch_id",
    "analytics.vehicleinteraction": "branch_id",
    "documents.privatedocument": "branch_id",
    "audit.auditlog": "branch_id",
    "audit.securityalert": "branch_id",
    "privacy.datasubjectrequest": "customer__assigned_branch_id",
    "privacy.dataexportjob": "customer__assigned_branch_id",
    "security_center.activesession": "user__branch_id",
    "api.webhookevent": "branch_id",
    "api.webhookdelivery": "event__branch_id",
    "api.integrationlog": "branch_id",
}


class APIClientBranchScopeFilterBackend(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        client = getattr(request, "api_client", None)
        if not client or not client.branch_id:
            return queryset
        label = queryset.model._meta.label_lower
        if label == "accounts.user":
            allowed_ids = users_in_branches_queryset((client.branch_id,), active_only=False).values("pk")
            return queryset.filter(pk__in=allowed_ids)
        if label == "inventory.stockmovement":
            return queryset.filter(
                Q(branch_id=client.branch_id) | Q(destination_branch_id=client.branch_id)
            ).distinct()
        if label == "privacy.consentrecord":
            return queryset.filter(
                Q(customer__assigned_branch_id=client.branch_id) | Q(lead__branch_id=client.branch_id)
            ).distinct()
        lookup = BRANCH_LOOKUPS.get(label)
        if lookup:
            return queryset.filter(**{lookup: client.branch_id})
        return queryset
