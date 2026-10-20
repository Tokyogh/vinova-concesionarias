"""ES: Este módulo registra modelos en la administración de Django para el dominio de analítica.

EN: This module registers models in Django admin for the analytics domain.

Contexto existente / Existing context:
Django admin registrations for the analytics domain.
"""

from django.contrib import admin

from apps.analytics.models import VehicleInteraction


@admin.register(VehicleInteraction)
class VehicleInteractionAdmin(admin.ModelAdmin):
    list_display = ("event_type", "vehicle", "lead", "branch", "city", "utm_source", "created_at")
    list_filter = ("event_type", "branch", "utm_source")
    search_fields = ("vehicle__internal_code", "lead__code", "city", "utm_campaign")
    readonly_fields = ("event_id", "created_at", "updated_at")
