"""ES: Este módulo registra modelos en la administración de Django para el dominio de API e integraciones.

EN: This module registers models in Django admin for the api domain.

Contexto existente / Existing context:
Django admin registrations for the api domain.
"""

from django.contrib import admin

from apps.api.models import APIClient, APIScope, IdempotencyRecord, IntegrationLog, WebhookDelivery, WebhookEndpoint, WebhookEvent


@admin.register(APIScope)
class APIScopeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_sensitive", "is_active")
    list_filter = ("is_sensitive", "is_active")
    search_fields = ("code", "name")


@admin.register(APIClient)
class APIClientAdmin(admin.ModelAdmin):
    list_display = ("name", "service_user", "branch", "is_active", "expires_at", "last_used_at")
    list_filter = ("is_active", "branch")
    search_fields = ("name", "service_user__email")
    filter_horizontal = ("scopes",)
    readonly_fields = ("public_id", "secret_digest", "secret_last_four", "last_used_at", "last_used_ip", "rotated_at")


@admin.register(WebhookEndpoint)
class WebhookEndpointAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "branch", "is_active", "last_success_at", "last_failure_at")
    list_filter = ("is_active", "branch")
    readonly_fields = ("public_id", "encrypted_secret", "secret_last_four", "rotated_at", "last_success_at", "last_failure_at")


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "event_type", "aggregate_type", "aggregate_id", "branch", "occurred_at")
    list_filter = ("event_type", "branch")
    readonly_fields = ("event_id", "payload")


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display = ("public_id", "endpoint", "event", "status", "attempts", "response_code", "created_at")
    list_filter = ("status", "endpoint")
    readonly_fields = ("public_id",)


@admin.register(IntegrationLog)
class IntegrationLogAdmin(admin.ModelAdmin):
    list_display = ("public_id", "direction", "category", "action", "status", "client", "http_status", "created_at")
    list_filter = ("direction", "category", "status")
    search_fields = ("action", "endpoint", "error_code", "error_message")
    readonly_fields = ("public_id", "payload_hash", "idempotency_key_hash", "metadata")


@admin.register(IdempotencyRecord)
class IdempotencyRecordAdmin(admin.ModelAdmin):
    list_display = ("client", "key_hint", "method", "path", "status", "expires_at")
    list_filter = ("status",)
    readonly_fields = ("key_hash", "request_hash", "response_body")
