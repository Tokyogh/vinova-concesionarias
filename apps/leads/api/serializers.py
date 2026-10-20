"""ES: Este módulo serializa y valida contratos de API para el dominio de CRM y leads.

EN: This module serializes and validates API contracts for the leads domain.

Contexto existente / Existing context:
REST serializers and API validation for the leads domain.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.accounts.scopes import accessible_branch_ids
from apps.customers.selectors import accessible_customer_queryset
from apps.common.validators import (
    validate_human_name,
    validate_no_unsafe_control_characters,
    validate_phone_number,
)
from apps.leads.models import Lead, LeadActivity, TestDrive
from apps.leads.selectors import (
    accessible_lead_advisors_queryset,
    accessible_lead_branches_queryset,
    accessible_lead_vehicles_queryset,
    scoped_lead_queryset,
)
from apps.leads.services import (
    add_lead_activity_from_data,
    create_internal_lead_from_data,
    schedule_test_drive_from_data,
)


LEAD_MANAGE_PERMISSION_CODES = ("leads.manage",)


def _request_user(serializer):
    request = serializer.context.get("request")
    return getattr(request, "user", None)


def _as_serializer_error(exc: DjangoValidationError):
    if hasattr(exc, "message_dict"):
        return serializers.ValidationError(exc.message_dict)
    return serializers.ValidationError(exc.messages)


class LeadSerializer(serializers.ModelSerializer):
    """ES: Agrupa el componente «lead serializer» del dominio de CRM y leads y sus reglas relacionadas. Además, rechaza estados o entradas inválidas.

    EN: Groups the «lead serializer» component and its related rules in the leads domain. It also rejects invalid input or state.
    """

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    request_type_display = serializers.CharField(source="get_request_type_display", read_only=True)
    vehicle_label = serializers.CharField(source="vehicle_interest_label", read_only=True)

    def get_fields(self):
        fields = super().get_fields()
        user = _request_user(self)
        fields["customer"].queryset = accessible_customer_queryset(
            user, permission_codes=LEAD_MANAGE_PERMISSION_CODES
        )
        fields["vehicle"].queryset = accessible_lead_vehicles_queryset(
            user, permission_codes=LEAD_MANAGE_PERMISSION_CODES
        )
        fields["branch"].queryset = accessible_lead_branches_queryset(
            user, permission_codes=LEAD_MANAGE_PERMISSION_CODES
        )
        fields["assigned_advisor"].queryset = accessible_lead_advisors_queryset(
            user, permission_codes=LEAD_MANAGE_PERMISSION_CODES
        )
        if accessible_branch_ids(user, permission_codes=LEAD_MANAGE_PERMISSION_CODES) is not None:
            fields["branch"].required = True
            fields["branch"].allow_null = False
        return fields

    def create(self, validated_data):
        try:
            return create_internal_lead_from_data(actor=_request_user(self), validated_data=validated_data)
        except DjangoValidationError as exc:
            raise _as_serializer_error(exc) from exc

    class Meta:
        model = Lead
        fields = [
            "id", "public_id", "code", "request_type", "request_type_display", "status", "status_display", "priority",
            "priority_display", "source", "full_name", "email", "phone", "whatsapp", "city", "province",
            "preferred_contact_method", "customer", "vehicle", "vehicle_label", "branch", "assigned_advisor", "linked_sale",
            "interested_brand", "interested_model", "budget_min", "budget_max", "expected_purchase_date", "message",
            "internal_notes", "lost_reason", "score", "last_contact_at", "next_follow_up_at", "closed_at", "created_at", "updated_at",
        ]
        read_only_fields = [
            "public_id",
            "code",
            "status",
            "linked_sale",
            "lost_reason",
            "score",
            "last_contact_at",
            "closed_at",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "full_name": {"validators": [validate_human_name]},
            "phone": {"validators": [validate_phone_number]},
            "whatsapp": {"validators": [validate_phone_number]},
            "city": {"validators": [validate_human_name]},
            "province": {"validators": [validate_human_name]},
            "message": {"validators": [validate_no_unsafe_control_characters]},
            "internal_notes": {"validators": [validate_no_unsafe_control_characters]},
            "budget_min": {"min_value": 0},
            "budget_max": {"min_value": 0},
        }


class LeadActivitySerializer(serializers.ModelSerializer):
    def get_fields(self):
        fields = super().get_fields()
        fields["lead"].queryset = scoped_lead_queryset(
            _request_user(self), permission_codes=LEAD_MANAGE_PERMISSION_CODES
        )
        return fields

    def create(self, validated_data):
        try:
            return add_lead_activity_from_data(actor=_request_user(self), validated_data=validated_data)
        except DjangoValidationError as exc:
            raise _as_serializer_error(exc) from exc

    class Meta:
        model = LeadActivity
        fields = [
            "id",
            "lead",
            "activity_type",
            "title",
            "detail",
            "outcome",
            "scheduled_for",
            "completed_at",
            "created_by",
            "created_at",
        ]
        read_only_fields = ["created_by", "created_at"]


class TestDriveSerializer(serializers.ModelSerializer):
    def get_fields(self):
        fields = super().get_fields()
        user = _request_user(self)
        fields["lead"].queryset = scoped_lead_queryset(
            user, permission_codes=LEAD_MANAGE_PERMISSION_CODES
        )
        fields["vehicle"].queryset = accessible_lead_vehicles_queryset(
            user, permission_codes=LEAD_MANAGE_PERMISSION_CODES
        )
        fields["branch"].queryset = accessible_lead_branches_queryset(
            user, permission_codes=LEAD_MANAGE_PERMISSION_CODES
        )
        fields["advisor"].queryset = accessible_lead_advisors_queryset(
            user, permission_codes=LEAD_MANAGE_PERMISSION_CODES
        )
        return fields

    def create(self, validated_data):
        try:
            return schedule_test_drive_from_data(actor=_request_user(self), validated_data=validated_data)
        except DjangoValidationError as exc:
            raise _as_serializer_error(exc) from exc

    class Meta:
        model = TestDrive
        fields = [
            "id",
            "lead",
            "vehicle",
            "branch",
            "advisor",
            "starts_at",
            "ends_at",
            "status",
            "notes",
            "result_notes",
            "created_by",
            "created_at",
        ]
        read_only_fields = ["status", "result_notes", "created_by", "created_at"]
