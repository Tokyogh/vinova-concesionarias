"""ES: Este módulo registra modelos en la administración de Django para el dominio de vehículos.

EN: This module registers models in Django admin for the vehicles domain.

Contexto existente / Existing context:
Django admin registrations for the vehicles domain.
"""

from django.contrib import admin
from apps.vehicles.models import (
    CustomerVehicle,
    Vehicle,
    VehicleBrand,
    VehicleCommercialHighlight,
    VehicleLinkCode,
    VehicleMedia,
    VehicleModel,
    VehiclePartSpecification,
    VehicleResource,
)


@admin.register(VehicleLinkCode)
class VehicleLinkCodeAdmin(admin.ModelAdmin):
    list_display = ["code", "vehicle", "status", "created_at", "expires_at"]
    search_fields = ["code", "vehicle__internal_code", "vehicle__vin", "vehicle__plate"]
    list_filter = ["status", "created_at"]
    autocomplete_fields = ["vehicle"]
    readonly_fields = ["code", "created_by", "used_by", "revoked_by"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CustomerVehicle)
class CustomerVehicleAdmin(admin.ModelAdmin):
    list_display = ["customer", "vehicle", "role_type", "is_active", "created_at"]
    search_fields = ["customer__first_name", "customer__last_name", "customer__business_name", "vehicle__internal_code", "vehicle__vin", "vehicle__plate"]
    list_filter = ["role_type", "is_active"]
    autocomplete_fields = ["customer", "vehicle"]
    readonly_fields = ["created_at", "updated_at"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class VehicleMediaInline(admin.TabularInline):
    model = VehicleMedia
    extra = 1
    autocomplete_fields = ["resource"]


class VehiclePartInline(admin.StackedInline):
    model = VehiclePartSpecification
    extra = 0
    autocomplete_fields = ["image"]


class VehicleHighlightInline(admin.TabularInline):
    model = VehicleCommercialHighlight
    extra = 0


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ["__str__", "internal_code", "vin", "plate", "branch", "status", "price", "is_featured"]
    search_fields = ["internal_code", "vin", "plate", "brand__name", "model__name", "version"]
    list_filter = ["status", "brand", "branch", "year", "is_featured"]
    autocomplete_fields = ["brand", "model", "branch"]
    inlines = [VehicleMediaInline, VehiclePartInline, VehicleHighlightInline]
    readonly_fields = [
        "brand",
        "model",
        "branch",
        "year",
        "version",
        "internal_code",
        "vin",
        "plate",
        "color",
        "mileage",
        "price",
        "status",
        "short_description",
        "description",
        "public_slug",
        "is_featured",
        "published_at",
        "is_deleted",
        "deleted_at",
        "created_at",
        "updated_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(VehicleBrand)
class VehicleBrandAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(VehicleModel)
class VehicleModelAdmin(admin.ModelAdmin):
    search_fields = ["name", "brand__name"]
    list_filter = ["brand", "segment", "is_active"]
    autocomplete_fields = ["brand"]


@admin.register(VehicleResource)
class VehicleResourceAdmin(admin.ModelAdmin):
    list_display = ["title", "resource_type", "is_reusable", "created_at"]
    search_fields = ["title", "file_hash"]
    list_filter = ["resource_type", "is_reusable"]
