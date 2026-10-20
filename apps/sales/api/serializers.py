"""ES: Este módulo serializa y valida contratos de API para el dominio de ventas.

EN: This module serializes and validates API contracts for the sales domain.

Contexto existente / Existing context:
REST serializers and API validation for the sales domain.
"""

from rest_framework import serializers

from apps.sales.models import SaleLine, SalePayment, SaleRecord, SaleStatusHistory
from apps.sales.services import create_sale_from_data


class SaleLineSerializer(serializers.ModelSerializer):
    item_label = serializers.CharField(source="item.__str__", read_only=True)

    class Meta:
        model = SaleLine
        fields = [
            "id",
            "sale",
            "item",
            "item_label",
            "description",
            "quantity",
            "unit_price",
            "discount_amount",
            "line_subtotal",
            "line_total",
            "reserved_quantity",
            "fulfilled_quantity",
            "notes",
            "created_at",
        ]
        read_only_fields = ["line_subtotal", "line_total", "reserved_quantity", "fulfilled_quantity", "created_at"]


class SalePaymentSerializer(serializers.ModelSerializer):
    received_by_label = serializers.CharField(source="received_by.get_full_name", read_only=True)

    class Meta:
        model = SalePayment
        fields = ["id", "sale", "method", "status", "amount", "reference", "paid_at", "received_by", "received_by_label", "notes", "created_at"]
        read_only_fields = ["received_by", "received_by_label", "created_at"]


class SaleStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_label = serializers.CharField(source="changed_by.get_full_name", read_only=True)

    class Meta:
        model = SaleStatusHistory
        fields = ["id", "sale", "previous_status", "new_status", "changed_by", "changed_by_label", "note", "metadata", "created_at"]
        read_only_fields = fields


class SaleRecordSerializer(serializers.ModelSerializer):
    """ES: Agrupa el componente «sale record serializer» del dominio de ventas y sus reglas relacionadas.

    EN: Groups the «sale record serializer» component and its related rules in the sales domain.
    """

    customer_label = serializers.CharField(source="customer.display_name", read_only=True)
    branch_label = serializers.CharField(source="branch.name", read_only=True)
    vehicle_label = serializers.CharField(source="vehicle.__str__", read_only=True)
    lines = SaleLineSerializer(many=True, read_only=True)
    payments = SalePaymentSerializer(many=True, read_only=True)

    class Meta:
        model = SaleRecord
        fields = [
            "id",
            "number",
            "kind",
            "status",
            "customer",
            "customer_label",
            "branch",
            "branch_label",
            "advisor",
            "vehicle",
            "vehicle_label",
            "source",
            "vehicle_price",
            "vehicle_discount",
            "line_subtotal",
            "discount_total",
            "subtotal",
            "tax_rate",
            "tax_total",
            "total",
            "amount_paid",
            "balance_due",
            "valid_until",
            "reserved_until",
            "closed_at",
            "notes",
            "internal_notes",
            "lines",
            "payments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "number",
            "status",
            "line_subtotal",
            "discount_total",
            "subtotal",
            "tax_total",
            "total",
            "amount_paid",
            "balance_due",
            "closed_at",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        request = self.context.get("request")
        actor = request.user if request and request.user.is_authenticated else None
        return create_sale_from_data(actor=actor, validated_data=validated_data, history_note="Operación creada desde API")
