"""ES: Este módulo serializa y valida contratos de API para el dominio de reportes.

EN: This module serializes and validates API contracts for the reports domain.

Contexto existente / Existing context:
REST serializers and API validation for the reports domain.
"""

from rest_framework import serializers

from apps.accounts.models import User
from apps.accounts.scopes import accessible_branches_queryset, accessible_users_queryset, scope_queryset_to_user_branches
from apps.branches.models import Branch
from apps.inventory.models import InventoryCategory
from apps.sales.models import SaleRecord
from apps.vehicles.models import Vehicle


class ReportFilterSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.none(), required=False)
    seller = serializers.PrimaryKeyRelatedField(queryset=User.objects.none(), required=False)
    sale_status = serializers.ChoiceField(choices=SaleRecord.Status.choices, required=False)
    vehicle = serializers.PrimaryKeyRelatedField(queryset=Vehicle.objects.none(), required=False)
    category = serializers.PrimaryKeyRelatedField(queryset=InventoryCategory.objects.none(), required=False)
    q = serializers.CharField(required=False, allow_blank=True, max_length=200)
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=200, default=50)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        self.fields["branch"].queryset = accessible_branches_queryset(
            getattr(request, "user", None),
            permission_codes=("reports.view",),
        )
        self.fields["seller"].queryset = accessible_users_queryset(
            getattr(request, "user", None),
            permission_codes=("reports.view",),
        )
        self.fields["vehicle"].queryset = scope_queryset_to_user_branches(
            Vehicle.objects.filter(is_deleted=False),
            user=getattr(request, "user", None),
            permission_codes=("reports.view",),
        )
        self.fields["category"].queryset = InventoryCategory.objects.filter(is_active=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs.get("start_date") and attrs.get("end_date") and attrs["start_date"] > attrs["end_date"]:
            raise serializers.ValidationError("La fecha desde no puede ser posterior a la fecha hasta.")
        return attrs
