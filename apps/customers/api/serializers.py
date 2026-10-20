"""ES: Este módulo serializa y valida contratos de API para el dominio de clientes.

EN: This module serializes and validates API contracts for the customers domain.

Contexto existente / Existing context:
REST serializers and API validation for the customers domain.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.accounts.scopes import accessible_branch_ids
from apps.customers.models import Customer, CustomerNote, CustomerVehicleInterest
from apps.customers.selectors import (
    accessible_customer_advisors_queryset,
    accessible_customer_branches_queryset,
    accessible_customer_queryset,
    accessible_customer_vehicles_queryset,
)
from apps.customers.services import (
    add_customer_note_from_data,
    add_vehicle_interest_from_data,
    create_customer_from_data,
    update_customer_from_data,
)
from apps.common.validators import (
    validate_human_name,
    validate_no_unsafe_control_characters,
    validate_phone_number,
)


CUSTOMER_MANAGE_PERMISSION_CODES = ("customers.manage",)


def _request_user(serializer):
    request = serializer.context.get("request")
    return getattr(request, "user", None)


def _as_serializer_error(exc: DjangoValidationError):
    if hasattr(exc, "message_dict"):
        return serializers.ValidationError(exc.message_dict)
    return serializers.ValidationError(exc.messages)


class CustomerSerializer(serializers.ModelSerializer):
    """ES: Agrupa el componente «customer serializer» del dominio de clientes y sus reglas relacionadas. Además, rechaza estados o entradas inválidas.

    EN: Groups the «customer serializer» component and its related rules in the customers domain. It also rejects invalid input or state.
    """

    display_name = serializers.CharField(read_only=True)
    primary_contact = serializers.CharField(read_only=True)

    def get_fields(self):
        fields = super().get_fields()
        user = _request_user(self)
        fields["assigned_branch"].queryset = accessible_customer_branches_queryset(
            user, permission_codes=CUSTOMER_MANAGE_PERMISSION_CODES
        )
        fields["assigned_advisor"].queryset = accessible_customer_advisors_queryset(
            user, permission_codes=CUSTOMER_MANAGE_PERMISSION_CODES
        )
        if accessible_branch_ids(user, permission_codes=CUSTOMER_MANAGE_PERMISSION_CODES) is not None:
            fields["assigned_branch"].required = True
            fields["assigned_branch"].allow_null = False
        return fields

    def create(self, validated_data):
        try:
            return create_customer_from_data(actor=_request_user(self), validated_data=validated_data)
        except DjangoValidationError as exc:
            raise _as_serializer_error(exc) from exc

    def update(self, instance, validated_data):
        try:
            return update_customer_from_data(
                actor=_request_user(self), customer=instance, validated_data=validated_data
            )
        except DjangoValidationError as exc:
            raise _as_serializer_error(exc) from exc

    class Meta:
        model = Customer
        fields = [
            "id",
            "customer_type",
            "identification_type",
            "identification_number",
            "first_name",
            "last_name",
            "business_name",
            "display_name",
            "email",
            "phone",
            "whatsapp",
            "primary_contact",
            "city",
            "province",
            "preferred_contact_method",
            "source",
            "status",
            "assigned_branch",
            "assigned_advisor",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["status", "created_at", "updated_at"]
        extra_kwargs = {
            "first_name": {"validators": [validate_human_name]},
            "last_name": {"validators": [validate_human_name]},
            "business_name": {"validators": [validate_no_unsafe_control_characters]},
            "phone": {"validators": [validate_phone_number]},
            "whatsapp": {"validators": [validate_phone_number]},
            "city": {"validators": [validate_human_name]},
            "province": {"validators": [validate_human_name]},
            "source": {"validators": [validate_no_unsafe_control_characters]},
        }


class CustomerNoteSerializer(serializers.ModelSerializer):
    def get_fields(self):
        fields = super().get_fields()
        fields["customer"].queryset = accessible_customer_queryset(
            _request_user(self), permission_codes=CUSTOMER_MANAGE_PERMISSION_CODES
        )
        return fields

    def create(self, validated_data):
        try:
            return add_customer_note_from_data(actor=_request_user(self), validated_data=validated_data)
        except DjangoValidationError as exc:
            raise _as_serializer_error(exc) from exc

    class Meta:
        model = CustomerNote
        fields = ["id", "customer", "note_type", "title", "body", "is_important", "created_by", "created_at"]
        read_only_fields = ["created_by", "created_at"]


class CustomerVehicleInterestSerializer(serializers.ModelSerializer):
    def get_fields(self):
        fields = super().get_fields()
        user = _request_user(self)
        fields["customer"].queryset = accessible_customer_queryset(
            user, permission_codes=CUSTOMER_MANAGE_PERMISSION_CODES
        )
        fields["vehicle"].queryset = accessible_customer_vehicles_queryset(
            user, permission_codes=CUSTOMER_MANAGE_PERMISSION_CODES
        )
        return fields

    def create(self, validated_data):
        try:
            return add_vehicle_interest_from_data(actor=_request_user(self), validated_data=validated_data)
        except DjangoValidationError as exc:
            raise _as_serializer_error(exc) from exc

    class Meta:
        model = CustomerVehicleInterest
        fields = ["id", "customer", "vehicle", "brand", "model_name", "year_from", "year_to", "budget_min", "budget_max", "status", "notes", "created_by", "created_at"]
        read_only_fields = ["created_by", "created_at"]
