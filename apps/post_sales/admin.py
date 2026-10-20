"""ES: Este módulo registra modelos en la administración de Django para el dominio de postventa.

EN: This module registers models in Django admin for the post sales domain.

Contexto existente / Existing context:
Django admin registrations for the post sales domain.
"""

from django.contrib import admin

from apps.common.modules import is_module_enabled
from apps.post_sales.models import ServiceOrder, ServiceOrderHistory, ServiceOrderLine


class ReadOnlyPostSalesAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return is_module_enabled("post_sales") and super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        return is_module_enabled("post_sales") and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ServiceOrder)
class ServiceOrderAdmin(ReadOnlyPostSalesAdmin):
    list_display = ("number", "branch", "customer", "vehicle", "responsible", "status", "total_cost")
    list_filter = ("status", "branch")
    search_fields = ("number", "customer__first_name", "customer__last_name", "vehicle__vin", "vehicle__plate")
    readonly_fields = ("total_cost", "created_by", "started_at", "completed_at")


@admin.register(ServiceOrderLine)
class ServiceOrderLineAdmin(ReadOnlyPostSalesAdmin):
    list_display = ("order", "line_type", "description", "quantity", "unit_cost", "total_cost")
    readonly_fields = ("total_cost",)


@admin.register(ServiceOrderHistory)
class ServiceOrderHistoryAdmin(ReadOnlyPostSalesAdmin):
    list_display = ("order", "previous_status", "new_status", "changed_by", "created_at")
    readonly_fields = tuple(field.name for field in ServiceOrderHistory._meta.fields)
