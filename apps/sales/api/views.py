"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de ventas.

EN: This module orchestrates HTTP requests, permissions, and responses for the sales domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the sales domain.
"""

from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_datetime
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from apps.sales.api.serializers import SaleLineSerializer, SalePaymentSerializer, SaleRecordSerializer, SaleStatusHistorySerializer
from apps.sales.models import SaleLine, SalePayment, SaleStatusHistory
from apps.sales.selectors import accessible_sales_queryset
from apps.sales.services import cancel_sale, confirm_sale, reserve_sale, void_sale_payment


class SalesApiPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return user.has_perm_code("sales.quote") or user.has_perm_code("sales.reserve") or user.has_perm_code("sales.sell")
        if view.action in {"reserve"}:
            return user.has_perm_code("sales.reserve")
        if view.action in {"confirm", "payments", "void"}:
            return user.has_perm_code("sales.sell")
        return user.has_perm_code("sales.quote") or user.has_perm_code("sales.sell")


class SaleRecordViewSet(viewsets.ModelViewSet):
    serializer_class = SaleRecordSerializer
    permission_classes = [SalesApiPermission]
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["kind", "status", "branch", "customer", "vehicle"]
    search_fields = ["number", "customer__first_name", "customer__last_name", "customer__business_name", "customer__identification_number", "vehicle__vin", "vehicle__plate"]
    ordering_fields = ["created_at", "total", "status"]

    def get_queryset(self):
        return accessible_sales_queryset(self.request.user).select_related("customer", "branch", "advisor", "vehicle", "vehicle__brand", "vehicle__model", "vehicle__model__brand").prefetch_related("lines", "payments")

    @action(detail=True, methods=["post"])
    def reserve(self, request, pk=None):
        sale = self.get_object()
        try:
            reserve_sale(actor=request.user, sale=sale, reserved_until=parse_datetime(request.data.get("reserved_until")) if request.data.get("reserved_until") else sale.reserved_until, note=request.data.get("note", ""))
        except ValidationError as exc:
            return Response({"detail": exc.message if hasattr(exc, "message") else str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(sale).data)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        sale = self.get_object()
        try:
            confirm_sale(actor=request.user, sale=sale, note=request.data.get("note", ""))
        except ValidationError as exc:
            return Response({"detail": exc.message if hasattr(exc, "message") else str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(sale).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        sale = self.get_object()
        try:
            cancel_sale(actor=request.user, sale=sale, note=request.data.get("note", ""))
        except ValidationError as exc:
            return Response({"detail": exc.message if hasattr(exc, "message") else str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(sale).data)


class SaleLineViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SaleLineSerializer
    permission_classes = [SalesApiPermission]
    filterset_fields = ["sale", "item"]
    search_fields = ["sale__number", "description", "item__sku", "item__name"]

    def get_queryset(self):
        return SaleLine.objects.filter(sale_id__in=accessible_sales_queryset(self.request.user).values("pk")).select_related("sale", "item")


class SalePaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SalePaymentSerializer
    permission_classes = [SalesApiPermission]
    filterset_fields = ["sale", "method", "status"]
    search_fields = ["sale__number", "reference"]

    def get_queryset(self):
        return SalePayment.objects.filter(sale_id__in=accessible_sales_queryset(self.request.user).values("pk")).select_related("sale", "received_by")

    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        payment = self.get_object()
        try:
            payment = void_sale_payment(
                actor=request.user,
                payment=payment,
                reason=request.data.get("reason", ""),
            )
        except ValidationError as exc:
            return Response(
                {"detail": exc.message if hasattr(exc, "message") else str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(self.get_serializer(payment).data)


class SaleStatusHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SaleStatusHistorySerializer
    permission_classes = [SalesApiPermission]
    filterset_fields = ["sale", "new_status"]

    def get_queryset(self):
        return SaleStatusHistory.objects.filter(sale_id__in=accessible_sales_queryset(self.request.user).values("pk")).select_related("sale", "changed_by")
