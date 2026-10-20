"""ES: Este módulo registra modelos en la administración de Django para el dominio de clientes.

EN: This module registers models in Django admin for the customers domain.

Contexto existente / Existing context:
Django admin registrations for the customers domain.
"""

from django.contrib import admin

from apps.customers.models import Customer, CustomerNote, CustomerVehicleInterest


class CustomerNoteInline(admin.TabularInline):
    model = CustomerNote
    extra = 0
    fields = ("note_type", "title", "is_important", "created_by", "created_at")
    readonly_fields = ("created_at",)


class CustomerVehicleInterestInline(admin.TabularInline):
    model = CustomerVehicleInterest
    extra = 0
    fields = ("vehicle", "brand", "model_name", "budget_min", "budget_max", "status", "created_by")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("display_name", "customer_type", "identification_number", "primary_contact", "assigned_branch", "status", "created_at")
    search_fields = ("first_name", "last_name", "business_name", "identification_number", "email", "phone", "whatsapp")
    list_filter = ("customer_type", "status", "assigned_branch", "province", "city")
    autocomplete_fields = ("assigned_branch", "assigned_advisor", "created_by")
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    inlines = [CustomerVehicleInterestInline, CustomerNoteInline]


@admin.register(CustomerVehicleInterest)
class CustomerVehicleInterestAdmin(admin.ModelAdmin):
    list_display = ("customer", "vehicle", "brand", "model_name", "status", "created_at")
    search_fields = ("customer__first_name", "customer__last_name", "customer__business_name", "brand", "model_name", "vehicle__vin")
    list_filter = ("status", "brand", "created_at")
    autocomplete_fields = ("customer", "vehicle", "created_by")


@admin.register(CustomerNote)
class CustomerNoteAdmin(admin.ModelAdmin):
    list_display = ("customer", "note_type", "title", "is_important", "created_by", "created_at")
    search_fields = ("customer__first_name", "customer__last_name", "customer__business_name", "title", "body")
    list_filter = ("note_type", "is_important", "created_at")
    autocomplete_fields = ("customer", "created_by")
