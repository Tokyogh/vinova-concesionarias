"""ES: Este módulo registra modelos en la administración de Django para el dominio de privacidad.

EN: This module registers models in Django admin for the privacy domain.

Contexto existente / Existing context:
Django admin registrations for the privacy domain.
"""

from django.contrib import admin

from apps.privacy.models import AnonymizationRecord, ConsentRecord, DataExportJob, DataSubjectRequest, RetentionPolicy


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    list_display = ("public_id", "subject_name", "purpose", "status", "accepted_at", "customer", "lead")
    list_filter = ("purpose", "status")
    search_fields = ("subject_name", "subject_email")


@admin.register(DataSubjectRequest)
class DataSubjectRequestAdmin(admin.ModelAdmin):
    list_display = ("public_id", "request_type", "status", "requester_name", "customer", "received_at", "due_at")
    list_filter = ("request_type", "status")
    search_fields = ("requester_name", "requester_email", "requester_phone")


admin.site.register(DataExportJob)
admin.site.register(RetentionPolicy)
admin.site.register(AnonymizationRecord)
