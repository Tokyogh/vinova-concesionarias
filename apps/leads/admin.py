"""ES: Este módulo registra modelos en la administración de Django para el dominio de CRM y leads.

EN: This module registers models in Django admin for the leads domain.

Contexto existente / Existing context:
Django admin registrations for the leads domain.
"""

from django.contrib import admin

from apps.leads.models import Lead, LeadActivity, TestDrive


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("code", "full_name", "request_type", "status", "priority", "source", "assigned_advisor", "branch", "created_at")
    list_filter = ("status", "priority", "request_type", "source", "branch")
    search_fields = ("code", "full_name", "email", "phone", "whatsapp", "city")
    readonly_fields = ("public_id", "code", "score", "consent_at", "created_at", "updated_at")


@admin.register(LeadActivity)
class LeadActivityAdmin(admin.ModelAdmin):
    list_display = ("lead", "activity_type", "title", "scheduled_for", "completed_at", "created_by", "created_at")
    list_filter = ("activity_type", "completed_at")
    search_fields = ("lead__code", "lead__full_name", "title", "detail")


@admin.register(TestDrive)
class TestDriveAdmin(admin.ModelAdmin):
    list_display = ("lead", "vehicle", "branch", "advisor", "starts_at", "status")
    list_filter = ("status", "branch")
    search_fields = ("lead__code", "lead__full_name", "vehicle__internal_code")
