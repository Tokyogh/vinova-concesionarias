"""ES: Este módulo registra modelos en la administración de Django para el dominio de notificaciones.

EN: This module registers models in Django admin for the notifications domain.

Contexto existente / Existing context:
Django admin registrations for the notifications domain.
"""

from django.contrib import admin

from apps.notifications.models import (
    Campaign,
    CampaignRecipient,
    CustomerNotificationPreference,
    NotificationMessage,
    NotificationRecipient,
    NotificationTemplate,
)


class NotificationRecipientInline(admin.TabularInline):
    model = NotificationRecipient
    extra = 0
    readonly_fields = ["read_at", "archived_at"]
    autocomplete_fields = ["user", "customer"]


@admin.register(NotificationMessage)
class NotificationMessageAdmin(admin.ModelAdmin):
    list_display = ["title", "message_type", "priority", "status", "sender", "sent_at"]
    list_filter = ["message_type", "priority", "status", "branch"]
    search_fields = ["title", "body", "sender__username", "sender__email"]
    autocomplete_fields = ["sender", "branch", "related_customer", "related_vehicle", "related_sale", "related_document", "template"]
    readonly_fields = ["created_at", "updated_at", "sent_at"]
    inlines = [NotificationRecipientInline]


@admin.register(NotificationRecipient)
class NotificationRecipientAdmin(admin.ModelAdmin):
    list_display = ["notification", "recipient_type", "display_name_snapshot", "status", "read_at"]
    list_filter = ["recipient_type", "status"]
    search_fields = ["notification__title", "display_name_snapshot", "email_snapshot", "user__email", "customer__email"]
    autocomplete_fields = ["notification", "user", "customer"]


@admin.register(CustomerNotificationPreference)
class CustomerNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        "customer",
        "invoice_updates",
        "document_updates",
        "service_updates",
        "general_alerts",
        "email_enabled",
    ]
    list_filter = [
        "invoice_updates",
        "document_updates",
        "service_updates",
        "general_alerts",
        "email_enabled",
    ]
    search_fields = ["customer__first_name", "customer__last_name", "customer__email"]
    autocomplete_fields = ["customer"]


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "template_type", "is_active", "created_at"]
    list_filter = ["template_type", "is_active"]
    search_fields = ["name", "subject", "body"]


class CampaignRecipientInline(admin.TabularInline):
    model = CampaignRecipient
    extra = 0
    can_delete = False
    readonly_fields = ["customer", "display_name_snapshot", "email_snapshot", "phone_snapshot", "rendered_subject", "rendered_body", "created_at"]


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ["name", "branch", "segment_type", "recipient_count", "status", "created_at"]
    list_filter = ["status", "segment_type", "branch"]
    search_fields = ["name", "subject", "body"]
    readonly_fields = [field.name for field in Campaign._meta.fields]
    inlines = [CampaignRecipientInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return bool(obj) and super().has_view_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False
