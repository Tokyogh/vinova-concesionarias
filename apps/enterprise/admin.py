"""ES: Este módulo registra modelos en la administración de Django para el dominio de configuración empresarial.

EN: This module registers models in Django admin for the enterprise domain.

Contexto existente / Existing context:
Django admin registrations for the enterprise domain.
"""

from django.contrib import admin

from apps.enterprise.models import ApprovalPolicy, CompanyPublicSettings


@admin.register(CompanyPublicSettings)
class CompanyPublicSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "public_email",
        "public_phone",
        "show_public_branches",
        "show_vehicle_prices",
        "allow_client_registration",
    )
    search_fields = ("company__commercial_name", "public_email", "public_phone")


@admin.register(ApprovalPolicy)
class ApprovalPolicyAdmin(admin.ModelAdmin):
    list_display = ("company", "action", "mode", "threshold_amount", "threshold_percent", "is_active")
    list_filter = ("mode", "action", "is_active")
    search_fields = ("company__commercial_name", "notes")
    filter_horizontal = ("applies_to_roles",)
