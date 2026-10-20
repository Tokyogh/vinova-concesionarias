"""ES: Este módulo registra modelos en la administración de Django para el dominio de facturación.

EN: This module registers models in Django admin for the invoices domain.

Contexto existente / Existing context:
Django admin registrations for the invoices domain.
"""

from django.contrib import admin

from apps.invoices.models import InvoiceLine, InvoicePaymentApplication, InvoiceRecord, InvoiceSequence, InvoiceStatusHistory


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
    readonly_fields = ("line_subtotal", "line_tax", "line_total")


class InvoicePaymentApplicationInline(admin.TabularInline):
    model = InvoicePaymentApplication
    extra = 0


@admin.register(InvoiceRecord)
class InvoiceRecordAdmin(admin.ModelAdmin):
    list_display = ("number", "invoice_type", "status", "customer_name", "branch", "issue_date", "total", "balance_due")
    list_filter = ("status", "invoice_type", "branch", "issue_date")
    search_fields = ("number", "customer_name", "customer_document", "authorization_number", "access_key")
    readonly_fields = ("subtotal", "discount_total", "tax_total", "total", "amount_paid", "balance_due", "issued_at", "voided_at")
    inlines = [InvoiceLineInline, InvoicePaymentApplicationInline]


@admin.register(InvoiceSequence)
class InvoiceSequenceAdmin(admin.ModelAdmin):
    list_display = ("branch", "prefix", "next_number", "padding", "is_active")
    list_filter = ("is_active", "branch")
    search_fields = ("branch__name", "prefix")


@admin.register(InvoiceStatusHistory)
class InvoiceStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("invoice", "previous_status", "new_status", "changed_by", "created_at")
    list_filter = ("new_status", "created_at")
    search_fields = ("invoice__number", "note")


@admin.register(InvoicePaymentApplication)
class InvoicePaymentApplicationAdmin(admin.ModelAdmin):
    list_display = ("invoice", "amount", "sale_payment", "applied_at", "applied_by")
    search_fields = ("invoice__number", "notes")
