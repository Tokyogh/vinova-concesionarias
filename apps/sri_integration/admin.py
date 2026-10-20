"""ES: Este módulo registra modelos en la administración de Django para el dominio de configuración SRI heredada.

EN: This module registers models in Django admin for the sri integration domain.

Contexto existente / Existing context:
Django admin registrations for the sri integration domain.
"""

from django.contrib import admin

from apps.sri_integration.models import SriConfiguration, SriEstablishment, SriSequence


@admin.register(SriConfiguration)
class SriConfigurationAdmin(admin.ModelAdmin):
    list_display = ("company", "ruc", "environment", "status", "certificate_expires_at")
    list_filter = ("environment", "status", "accounting_required")
    search_fields = ("company__commercial_name", "ruc", "legal_name")


@admin.register(SriEstablishment)
class SriEstablishmentAdmin(admin.ModelAdmin):
    list_display = ("configuration", "establishment_code", "emission_point_code", "name", "branch", "is_default", "is_active")
    list_filter = ("is_default", "is_active")
    search_fields = ("name", "establishment_code", "emission_point_code")


@admin.register(SriSequence)
class SriSequenceAdmin(admin.ModelAdmin):
    list_display = ("establishment", "document_type", "current_number", "next_number_preview", "is_active")
    list_filter = ("document_type", "is_active")
