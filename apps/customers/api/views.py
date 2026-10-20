"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de clientes.

EN: This module orchestrates HTTP requests, permissions, and responses for the customers domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the customers domain.
"""

from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.permissions import require_perm_code
from apps.customers.api.serializers import CustomerNoteSerializer, CustomerSerializer, CustomerVehicleInterestSerializer
from apps.customers.models import CustomerNote, CustomerVehicleInterest
from apps.customers.selectors import accessible_customer_queryset, customer_list_queryset
from apps.customers.services import activate_customer, archive_customer, soft_delete_customer


CUSTOMER_MANAGE_PERMISSION_CODES = ("customers.manage",)


class CreateReadOnlyModelViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    pass


class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    search_fields = ["first_name", "last_name", "business_name", "identification_number", "email", "phone", "whatsapp", "city"]
    filterset_fields = ["customer_type", "status", "assigned_branch", "assigned_advisor"]
    ordering_fields = ["created_at", "last_name", "business_name", "status"]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        action = getattr(self, "action", None)
        if action in ["list", "retrieve"]:
            if not (request.user.has_perm_code("customers.view") or request.user.has_perm_code("customers.manage")):
                raise PermissionDenied("No tienes permisos para consultar clientes.")
        else:
            require_perm_code(request.user, "customers.manage")

    def get_queryset(self):
        return customer_list_queryset(user=self.request.user, query="")

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        soft_delete_customer(actor=self.request.user, customer=instance)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        customer = archive_customer(actor=request.user, customer=self.get_object())
        return Response(self.get_serializer(customer).data)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        customer = activate_customer(actor=request.user, customer=self.get_object())
        return Response(self.get_serializer(customer).data)


class CustomerNoteViewSet(CreateReadOnlyModelViewSet):
    serializer_class = CustomerNoteSerializer
    search_fields = ["title", "body", "customer__first_name", "customer__last_name", "customer__business_name"]
    filterset_fields = ["customer", "note_type", "is_important"]
    ordering_fields = ["created_at"]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        require_perm_code(request.user, "customers.manage")

    def get_queryset(self):
        customers = accessible_customer_queryset(
            self.request.user, permission_codes=CUSTOMER_MANAGE_PERMISSION_CODES
        )
        return CustomerNote.objects.select_related("customer", "created_by").filter(customer__in=customers)

    def perform_create(self, serializer):
        serializer.save()


class CustomerVehicleInterestViewSet(CreateReadOnlyModelViewSet):
    serializer_class = CustomerVehicleInterestSerializer
    search_fields = ["brand", "model_name", "customer__first_name", "customer__last_name", "customer__business_name"]
    filterset_fields = ["customer", "status", "vehicle"]
    ordering_fields = ["created_at"]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        require_perm_code(request.user, "customers.manage")

    def get_queryset(self):
        customers = accessible_customer_queryset(
            self.request.user, permission_codes=CUSTOMER_MANAGE_PERMISSION_CODES
        )
        return CustomerVehicleInterest.objects.select_related("customer", "vehicle", "created_by").filter(
            customer__in=customers
        )

    def perform_create(self, serializer):
        serializer.save()
