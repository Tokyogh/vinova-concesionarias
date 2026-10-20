"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de facturación.

EN: This module orchestrates HTTP requests, permissions, and responses for the invoices domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the invoices domain.
"""

from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.accounts.scopes import accessible_branch_ids
from apps.invoices.api.serializers import InvoiceLineSerializer, InvoicePaymentApplicationSerializer, InvoiceRecordSerializer, InvoiceSequenceSerializer, InvoiceStatusHistorySerializer
from apps.invoices.models import InvoiceLine, InvoicePaymentApplication, InvoiceSequence, InvoiceStatusHistory
from apps.invoices.selectors import INVOICE_SCOPE_PERMISSIONS, accessible_invoices_queryset, invoice_metrics, ready_sales_for_invoicing_queryset
from apps.sales.api.serializers import SaleRecordSerializer


class InvoiceApiPermissionMixin:
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        user = request.user
        if not (user.has_perm_code("invoices.view") or user.has_perm_code("invoices.issue") or user.has_perm_code("invoices.manage") or user.is_superuser):
            self.permission_denied(request, message="No tienes permisos de facturación.")


class InvoiceRecordViewSet(InvoiceApiPermissionMixin, ReadOnlyModelViewSet):
    serializer_class = InvoiceRecordSerializer
    filterset_fields = ["status", "invoice_type", "branch", "customer", "sale"]
    search_fields = ["number", "customer_name", "customer_document", "authorization_number", "access_key", "sale__number"]
    ordering_fields = ["issue_date", "created_at", "total", "balance_due"]

    def get_queryset(self):
        return accessible_invoices_queryset(self.request.user).select_related("company", "branch", "customer", "sale")

    @action(detail=False, methods=["get"])
    def metrics(self, request):
        return Response(invoice_metrics(request.user))

    @action(detail=False, methods=["get"], url_path="ready-sales")
    def ready_sales(self, request):
        serializer = SaleRecordSerializer(ready_sales_for_invoicing_queryset(request.user)[:50], many=True, context={"request": request})
        return Response(serializer.data)


class InvoiceLineViewSet(InvoiceApiPermissionMixin, ReadOnlyModelViewSet):
    serializer_class = InvoiceLineSerializer
    filterset_fields = ["invoice"]

    def get_queryset(self):
        return InvoiceLine.objects.filter(invoice_id__in=accessible_invoices_queryset(self.request.user).values("pk")).select_related("invoice", "source_sale_line")


class InvoicePaymentApplicationViewSet(InvoiceApiPermissionMixin, ReadOnlyModelViewSet):
    serializer_class = InvoicePaymentApplicationSerializer
    filterset_fields = ["invoice", "sale_payment"]

    def get_queryset(self):
        return InvoicePaymentApplication.objects.filter(invoice_id__in=accessible_invoices_queryset(self.request.user).values("pk")).select_related("invoice", "sale_payment", "applied_by")


class InvoiceSequenceViewSet(InvoiceApiPermissionMixin, ReadOnlyModelViewSet):
    serializer_class = InvoiceSequenceSerializer
    filterset_fields = ["branch", "prefix", "is_active"]

    def get_queryset(self):
        qs = InvoiceSequence.objects.select_related("branch")
        branch_ids = accessible_branch_ids(self.request.user, permission_codes=INVOICE_SCOPE_PERMISSIONS)
        if branch_ids is not None:
            qs = qs.filter(branch_id__in=branch_ids)
        return qs


class InvoiceStatusHistoryViewSet(InvoiceApiPermissionMixin, ReadOnlyModelViewSet):
    serializer_class = InvoiceStatusHistorySerializer
    filterset_fields = ["invoice", "new_status"]

    def get_queryset(self):
        return InvoiceStatusHistory.objects.filter(invoice_id__in=accessible_invoices_queryset(self.request.user).values("pk")).select_related("invoice", "changed_by")
