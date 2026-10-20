"""ES: Este módulo serializa y valida contratos de API para el dominio de API e integraciones.

EN: This module serializes and validates API contracts for the api domain.

Contexto existente / Existing context:
REST serializers and API validation for the api domain.
"""

from __future__ import annotations

from rest_framework import serializers

from apps.accounts.scopes import users_in_branches_queryset
from apps.api.models import APIClient, APIScope, IntegrationLog, WebhookDelivery, WebhookEndpoint, WebhookEvent
from apps.api.selectors import integration_branch_ids
from apps.api.validators import validate_webhook_url
from apps.common.validators import (
    validate_human_name,
    validate_no_unsafe_control_characters,
    validate_phone_number,
)
from apps.leads.models import Lead


class APIScopeSerializer(serializers.ModelSerializer):
    class Meta:
        model = APIScope
        fields = ["id", "code", "name", "description", "is_sensitive", "is_active"]
        read_only_fields = fields


class APIClientSerializer(serializers.ModelSerializer):
    scopes = serializers.SlugRelatedField(slug_field="code", queryset=APIScope.objects.filter(is_active=True), many=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    service_user_email = serializers.EmailField(source="service_user.email", read_only=True)

    class Meta:
        model = APIClient
        fields = [
            "id", "public_id", "name", "description", "service_user", "service_user_email", "branch", "branch_name",
            "scopes", "is_active", "expires_at", "allowed_ip_networks", "rate_limit", "secret_last_four",
            "rotated_at", "last_used_at", "last_used_ip", "created_at", "updated_at",
        ]
        read_only_fields = [
            "public_id", "secret_last_four", "rotated_at", "last_used_at", "last_used_ip", "created_at", "updated_at",
        ]

    def validate(self, attrs):
        instance = self.instance or APIClient()
        for key, value in attrs.items():
            if key != "scopes":
                setattr(instance, key, value)
        request = self.context.get("request")
        branch_ids = integration_branch_ids(request.user, ("integrations.manage",)) if request else None
        if branch_ids is not None:
            if not instance.branch_id or instance.branch_id not in branch_ids:
                raise serializers.ValidationError({"branch": "La sucursal está fuera de tu alcance de integraciones."})
            if (
                not instance.service_user_id
                or not users_in_branches_queryset((instance.branch_id,)).filter(pk=instance.service_user_id).exists()
            ):
                raise serializers.ValidationError({"service_user": "Selecciona un usuario de servicio de la misma sucursal."})
        instance.clean()
        return attrs


class APIClientIssuedSerializer(APIClientSerializer):
    token = serializers.CharField(read_only=True)
    token_notice = serializers.CharField(read_only=True)

    class Meta(APIClientSerializer.Meta):
        fields = [*APIClientSerializer.Meta.fields, "token", "token_notice"]
        read_only_fields = [*APIClientSerializer.Meta.read_only_fields, "token", "token_notice"]


class APIClientTokenResponseSerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    token = serializers.CharField()
    token_notice = serializers.CharField()


class StatusResponseSerializer(serializers.Serializer):
    status = serializers.CharField()


class WebhookEndpointSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = WebhookEndpoint
        fields = [
            "id", "public_id", "name", "url", "event_types", "branch", "branch_name", "is_active", "secret_last_four",
            "timeout_seconds", "max_retries", "rotated_at", "last_success_at", "last_failure_at", "created_at", "updated_at",
        ]
        read_only_fields = [
            "public_id", "secret_last_four", "rotated_at", "last_success_at", "last_failure_at", "created_at", "updated_at",
        ]

    def validate_url(self, value):
        validate_webhook_url(value)
        return value

    def validate_event_types(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError("Selecciona al menos un tipo de evento o usa '*'.")
        normalized = sorted({str(item).strip() for item in value if str(item).strip()})
        if not normalized:
            raise serializers.ValidationError("La lista de eventos no puede quedar vacía.")
        return normalized

    def validate(self, attrs):
        instance = self.instance or WebhookEndpoint()
        for key, value in attrs.items():
            setattr(instance, key, value)
        request = self.context.get("request")
        branch_ids = integration_branch_ids(request.user, ("integrations.manage",)) if request else None
        if branch_ids is not None and (not instance.branch_id or instance.branch_id not in branch_ids):
            raise serializers.ValidationError({"branch": "La sucursal está fuera de tu alcance de integraciones."})
        instance.clean()
        return attrs


class WebhookEndpointIssuedSerializer(WebhookEndpointSerializer):
    signing_secret = serializers.CharField(read_only=True)
    secret_notice = serializers.CharField(read_only=True)

    class Meta(WebhookEndpointSerializer.Meta):
        fields = [*WebhookEndpointSerializer.Meta.fields, "signing_secret", "secret_notice"]
        read_only_fields = [*WebhookEndpointSerializer.Meta.read_only_fields, "signing_secret", "secret_notice"]


class WebhookSecretResponseSerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    signing_secret = serializers.CharField()
    secret_notice = serializers.CharField()


class WebhookTestResponseSerializer(serializers.Serializer):
    event_id = serializers.UUIDField()
    status = serializers.CharField()


class QueuedTaskResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    task_id = serializers.CharField()


class WebhookEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEvent
        fields = ["event_id", "event_type", "aggregate_type", "aggregate_id", "branch", "payload", "occurred_at", "created_at"]
        read_only_fields = fields


class WebhookDeliverySerializer(serializers.ModelSerializer):
    endpoint_name = serializers.CharField(source="endpoint.name", read_only=True)
    event_type = serializers.CharField(source="event.event_type", read_only=True)
    event_id = serializers.UUIDField(source="event.event_id", read_only=True)

    class Meta:
        model = WebhookDelivery
        fields = [
            "public_id", "endpoint", "endpoint_name", "event", "event_id", "event_type", "status", "attempts",
            "celery_task_id", "response_code", "response_excerpt", "error_message", "next_retry_at", "delivered_at", "created_at",
        ]
        read_only_fields = fields


class IntegrationLogSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = IntegrationLog
        fields = [
            "public_id", "direction", "category", "action", "status", "client", "client_name", "user", "user_email",
            "branch", "branch_name", "request_id", "endpoint", "http_method", "http_status", "duration_ms", "payload_hash",
            "error_code", "error_message", "metadata", "created_at",
        ]
        read_only_fields = fields


class BIDatasetCatalogItemSerializer(serializers.Serializer):
    name = serializers.CharField()
    contains_personal_data = serializers.BooleanField()
    note = serializers.CharField(required=False)


class BIDatasetCatalogResponseSerializer(serializers.Serializer):
    schema_version = serializers.CharField()
    datasets = BIDatasetCatalogItemSerializer(many=True)
    filters = serializers.ListField(child=serializers.CharField())
    formats = serializers.ListField(child=serializers.CharField())
    max_limit = serializers.IntegerField()


class BIDatasetResponseSerializer(serializers.Serializer):
    dataset = serializers.CharField()
    schema_version = serializers.CharField()
    generated_at = serializers.DateTimeField()
    count = serializers.IntegerField()
    total = serializers.IntegerField()
    offset = serializers.IntegerField()
    limit = serializers.IntegerField()
    columns = serializers.ListField(child=serializers.CharField())
    results = serializers.ListField(child=serializers.DictField())


class AccountingExportResponseSerializer(serializers.Serializer):
    dataset = serializers.CharField()
    schema_version = serializers.CharField()
    generated_at = serializers.DateTimeField()
    count = serializers.IntegerField()
    total = serializers.IntegerField()
    offset = serializers.IntegerField()
    limit = serializers.IntegerField()
    results = serializers.ListField(child=serializers.DictField())


class ExternalLeadResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    public_id = serializers.UUIDField()
    code = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()


class ExternalLeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = [
            "request_type", "priority", "source", "full_name", "email", "phone", "whatsapp", "city", "province",
            "preferred_contact_method", "vehicle", "branch", "interested_brand", "interested_model", "budget_min", "budget_max",
            "expected_purchase_date", "message", "consent_data_processing", "source_url", "utm_source", "utm_medium", "utm_campaign",
        ]
        extra_kwargs = {
            "source": {"required": False},
            "priority": {"required": False},
            "request_type": {"required": False},
            "branch": {"required": False},
            "full_name": {"validators": [validate_human_name]},
            "phone": {"validators": [validate_phone_number]},
            "whatsapp": {"validators": [validate_phone_number]},
            "city": {"validators": [validate_human_name]},
            "province": {"validators": [validate_human_name]},
            "message": {"validators": [validate_no_unsafe_control_characters]},
            "budget_min": {"min_value": 0},
            "budget_max": {"min_value": 0},
        }

    def validate(self, attrs):
        if not (attrs.get("email") or attrs.get("phone") or attrs.get("whatsapp")):
            raise serializers.ValidationError("El lead necesita correo, teléfono o WhatsApp.")
        client = self.context.get("api_client")
        if client and client.branch_id:
            provided = attrs.get("branch")
            if provided and provided.pk != client.branch_id:
                raise serializers.ValidationError({"branch": "La sucursal está fuera del alcance del cliente API."})
            attrs["branch"] = client.branch
        return attrs

    def create(self, validated_data):
        lead = Lead(**validated_data)
        lead.full_clean()
        lead.save()
        return lead
