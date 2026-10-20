"""ES: Este módulo serializa y valida contratos de API para el dominio de facturación.

EN: This module serializes and validates API contracts for the invoices domain.

Contexto existente / Existing context:
REST serializers and API validation for the invoices domain.
"""

from rest_framework import serializers

from apps.invoices.models import InvoiceLine, InvoicePaymentApplication, InvoiceRecord, InvoiceSequence, InvoiceStatusHistory


class InvoiceSequenceSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = InvoiceSequence
        fields = ["id", "branch", "branch_name", "prefix", "next_number", "padding", "is_active"]


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = ["id", "invoice", "description", "quantity", "unit_price", "discount_amount", "tax_rate", "line_subtotal", "line_tax", "line_total", "source_sale_line"]
        read_only_fields = ["line_subtotal", "line_tax", "line_total"]


class InvoicePaymentApplicationSerializer(serializers.ModelSerializer):
    applied_by_name = serializers.CharField(source="applied_by.get_full_name", read_only=True)

    class Meta:
        model = InvoicePaymentApplication
        fields = ["id", "invoice", "sale_payment", "amount", "applied_at", "notes", "applied_by", "applied_by_name"]
        read_only_fields = ["applied_by"]


class InvoiceRecordSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    company_name = serializers.CharField(source="company.commercial_name", read_only=True)
    sale_number = serializers.CharField(source="sale.number", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    invoice_type_display = serializers.CharField(source="get_invoice_type_display", read_only=True)

    class Meta:
        model = InvoiceRecord
        fields = [
            "id", "number", "invoice_type", "invoice_type_display", "status", "status_display", "sale", "sale_number", "company", "company_name", "branch", "branch_name", "customer", "customer_name", "customer_document", "customer_email", "customer_phone", "issue_date", "due_date", "currency", "subtotal", "discount_total", "tax_total", "total", "amount_paid", "balance_due", "authorization_number", "access_key", "external_reference", "linked_document", "created_at", "updated_at",
        ]
        read_only_fields = ["number", "subtotal", "discount_total", "tax_total", "total", "amount_paid", "balance_due"]


class InvoiceStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source="changed_by.get_full_name", read_only=True)

    class Meta:
        model = InvoiceStatusHistory
        fields = ["id", "invoice", "previous_status", "new_status", "changed_by", "changed_by_name", "note", "metadata", "created_at"]
