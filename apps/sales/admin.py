"""ES: Este módulo registra modelos en la administración de Django para el dominio de ventas.

EN: This module registers models in Django admin for the sales domain.

Contexto existente / Existing context:
Django admin registrations for the sales domain.
"""

from django.contrib import admin

from apps.sales.models import SaleLine, SalePayment, SaleRecord, SaleStatusHistory


class SaleLineInline(admin.TabularInline):
    model = SaleLine
    extra = 0
    fields = ("item", "description", "quantity", "unit_price", "discount_amount", "line_total", "reserved_quantity", "fulfilled_quantity")
    readonly_fields = ("line_total", "reserved_quantity", "fulfilled_quantity")


class SalePaymentInline(admin.TabularInline):
    model = SalePayment
    extra = 0
    fields = ("method", "status", "amount", "reference", "paid_at", "received_by")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(SaleRecord)
class SaleRecordAdmin(admin.ModelAdmin):
    list_display = ("number", "kind", "status", "customer", "branch", "vehicle", "total", "balance_due", "created_at")
    list_filter = ("kind", "status", "branch", "source", "created_at")
    search_fields = ("number", "customer__first_name", "customer__last_name", "customer__business_name", "customer__identification_number", "vehicle__vin", "vehicle__plate")
    readonly_fields = ("number", "line_subtotal", "discount_total", "subtotal", "tax_total", "total", "amount_paid", "balance_due", "created_at", "updated_at")
    inlines = (SaleLineInline, SalePaymentInline)


@admin.register(SaleLine)
class SaleLineAdmin(admin.ModelAdmin):
    list_display = ("sale", "item", "description", "quantity", "unit_price", "line_total")
    search_fields = ("sale__number", "description", "item__sku", "item__name")


@admin.register(SalePayment)
class SalePaymentAdmin(admin.ModelAdmin):
    list_display = ("sale", "method", "status", "amount", "reference", "paid_at")
    list_filter = ("method", "status", "paid_at")
    search_fields = ("sale__number", "reference")
    readonly_fields = (
        "sale",
        "method",
        "status",
        "amount",
        "reference",
        "paid_at",
        "received_by",
        "notes",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SaleStatusHistory)
class SaleStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("sale", "previous_status", "new_status", "changed_by", "created_at")
    list_filter = ("new_status", "created_at")
    search_fields = ("sale__number", "note")
