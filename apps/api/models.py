"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de API e integraciones.

EN: This module defines persistent models, states, and constraints for the api domain.

Contexto existente / Existing context:
Persistent domain models and database constraints for the api domain.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import secrets
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.api.validators import validate_api_rate_limit, validate_webhook_url
from apps.common.models import TimeStampedModel


class APIScope(TimeStampedModel):
    code = models.CharField(max_length=80, unique=True, db_index=True)
    name = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    is_sensitive = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "Alcance API"
        verbose_name_plural = "Alcances API"

    def __str__(self):
        return self.code


class APIClient(TimeStampedModel):
    """ES: Agrupa el componente «a p i client» del dominio de API e integraciones y sus reglas relacionadas. Además, rechaza estados o entradas inválidas.

    EN: Groups the «a p i client» component and its related rules in the api domain. It also rejects invalid input or state.
    """

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    service_user = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="api_clients")
    branch = models.ForeignKey("branches.Branch", null=True, blank=True, on_delete=models.PROTECT, related_name="api_clients")
    scopes = models.ManyToManyField(APIScope, blank=True, related_name="clients")
    is_active = models.BooleanField(default=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    allowed_ip_networks = models.TextField(blank=True, help_text="CIDR o IP, una por línea o separadas por coma.")
    rate_limit = models.CharField(
        max_length=30,
        default="600/hour",
        validators=[validate_api_rate_limit],
    )
    secret_digest = models.CharField(max_length=64, blank=True)
    secret_last_four = models.CharField(max_length=4, blank=True)
    created_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="created_api_clients")
    rotated_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="rotated_api_clients")
    rotated_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_used_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["is_active", "expires_at"])]
        verbose_name = "Cliente API"
        verbose_name_plural = "Clientes API"

    def __str__(self):
        return self.name

    @property
    def is_expired(self):
        return bool(self.expires_at and self.expires_at <= timezone.now())

    def scope_codes(self):
        return set(self.scopes.filter(is_active=True).values_list("code", flat=True))

    def has_scope(self, required: str) -> bool:
        codes = self.scope_codes()
        if "*" in codes or required in codes:
            return True
        namespace = required.split(":", 1)[0]
        return f"{namespace}:*" in codes

    def _pepper(self) -> bytes:
        pepper = getattr(settings, "VINOVA_API_TOKEN_PEPPER", settings.SECRET_KEY)
        return str(pepper).encode("utf-8")

    def set_secret(self, raw_secret: str):
        self.secret_digest = hmac.new(self._pepper(), raw_secret.encode("utf-8"), hashlib.sha256).hexdigest()
        self.secret_last_four = raw_secret[-4:]

    def verify_secret(self, raw_secret: str) -> bool:
        expected = hmac.new(self._pepper(), raw_secret.encode("utf-8"), hashlib.sha256).hexdigest()
        return bool(self.secret_digest and hmac.compare_digest(expected, self.secret_digest))

    def issue_token(self) -> str:
        raw_secret = secrets.token_urlsafe(36)
        self.set_secret(raw_secret)
        self.rotated_at = timezone.now()
        self.save(update_fields=["secret_digest", "secret_last_four", "rotated_at", "updated_at"])
        return f"vnp_{self.public_id.hex}.{raw_secret}"

    def parsed_networks(self):
        values = self.allowed_ip_networks.replace(",", "\n").splitlines()
        networks = []
        for value in values:
            value = value.strip()
            if value:
                networks.append(ipaddress.ip_network(value, strict=False))
        return networks

    def allows_ip(self, value: str) -> bool:
        networks = self.parsed_networks()
        if not networks:
            return True
        try:
            address = ipaddress.ip_address(value)
        except ValueError:
            return False
        return any(address in network for network in networks)

    def clean(self):
        validate_api_rate_limit(self.rate_limit)
        try:
            self.parsed_networks()
        except ValueError as exc:
            raise ValidationError({"allowed_ip_networks": f"IP o CIDR inválido: {exc}"}) from exc
        if self.branch_id and self.service_user_id and self.service_user.branch_id not in {None, self.branch_id}:
            if not self.service_user.user_roles.filter(is_active=True, role__is_active=True, branch__isnull=True).exists():
                raise ValidationError({"branch": "La sucursal debe coincidir con el alcance del usuario de servicio."})


class IdempotencyRecord(TimeStampedModel):
    class Status(models.TextChoices):
        PROCESSING = "processing", "Procesando"
        COMPLETED = "completed", "Completado"
        FAILED = "failed", "Fallido"

    client = models.ForeignKey(APIClient, on_delete=models.CASCADE, related_name="idempotency_records")
    key_hash = models.CharField(max_length=64)
    key_hint = models.CharField(max_length=20, blank=True)
    method = models.CharField(max_length=12)
    path = models.CharField(max_length=500)
    request_hash = models.CharField(max_length=64)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROCESSING, db_index=True)
    response_status = models.PositiveSmallIntegerField(null=True, blank=True)
    response_body = models.JSONField(default=dict, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["client", "key_hash"], name="uniq_api_client_idempotency_key")]
        indexes = [models.Index(fields=["client", "status", "expires_at"])]
        verbose_name = "Registro de idempotencia"
        verbose_name_plural = "Registros de idempotencia"


class IntegrationLog(TimeStampedModel):
    class Direction(models.TextChoices):
        INBOUND = "inbound", "Entrante"
        OUTBOUND = "outbound", "Saliente"
        INTERNAL = "internal", "Interno"

    class Status(models.TextChoices):
        SUCCESS = "success", "Correcto"
        FAILED = "failed", "Fallido"
        DENIED = "denied", "Denegado"
        PENDING = "pending", "Pendiente"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    direction = models.CharField(max_length=20, choices=Direction.choices, db_index=True)
    category = models.CharField(max_length=60, db_index=True)
    action = models.CharField(max_length=120, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, db_index=True)
    client = models.ForeignKey(APIClient, null=True, blank=True, on_delete=models.SET_NULL, related_name="integration_logs")
    user = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="integration_logs")
    branch = models.ForeignKey("branches.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="integration_logs")
    request_id = models.UUIDField(null=True, blank=True, db_index=True)
    endpoint = models.CharField(max_length=500, blank=True)
    http_method = models.CharField(max_length=12, blank=True)
    http_status = models.PositiveSmallIntegerField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    payload_hash = models.CharField(max_length=64, blank=True)
    idempotency_key_hash = models.CharField(max_length=64, blank=True)
    error_code = models.CharField(max_length=80, blank=True)
    error_message = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["category", "status", "-created_at"]),
            models.Index(fields=["client", "-created_at"]),
        ]
        verbose_name = "Log de integración"
        verbose_name_plural = "Logs de integración"


class WebhookEndpoint(TimeStampedModel):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=140)
    url = models.URLField(max_length=500)
    event_types = models.JSONField(default=list, blank=True)
    branch = models.ForeignKey("branches.Branch", null=True, blank=True, on_delete=models.PROTECT, related_name="webhook_endpoints")
    is_active = models.BooleanField(default=True, db_index=True)
    encrypted_secret = models.TextField(blank=True)
    secret_last_four = models.CharField(max_length=4, blank=True)
    timeout_seconds = models.PositiveSmallIntegerField(default=10)
    max_retries = models.PositiveSmallIntegerField(default=5)
    created_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="created_webhooks")
    rotated_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_failure_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Endpoint webhook"
        verbose_name_plural = "Endpoints webhook"

    def __str__(self):
        return self.name

    def subscribes_to(self, event_type: str) -> bool:
        return "*" in self.event_types or event_type in self.event_types

    def clean(self):
        validate_webhook_url(self.url)
        if not isinstance(self.event_types, list) or not self.event_types:
            raise ValidationError({"event_types": "Registra al menos un tipo de evento o usa '*'."})
        normalized = sorted({str(item).strip() for item in self.event_types if str(item).strip()})
        if not normalized:
            raise ValidationError({"event_types": "La lista de eventos no puede quedar vacía."})
        self.event_types = normalized
        if not 2 <= self.timeout_seconds <= 30:
            raise ValidationError({"timeout_seconds": "Debe estar entre 2 y 30 segundos."})
        if not 1 <= self.max_retries <= 10:
            raise ValidationError({"max_retries": "Debe estar entre 1 y 10 intentos."})


class WebhookEvent(TimeStampedModel):
    event_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    event_type = models.CharField(max_length=100, db_index=True)
    aggregate_type = models.CharField(max_length=80, blank=True, db_index=True)
    aggregate_id = models.CharField(max_length=100, blank=True, db_index=True)
    branch = models.ForeignKey("branches.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="webhook_events")
    payload = models.JSONField(default=dict)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [models.Index(fields=["event_type", "-occurred_at"])]
        verbose_name = "Evento webhook"
        verbose_name_plural = "Eventos webhook"


class WebhookDelivery(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        SENDING = "sending", "Enviando"
        RETRYING = "retrying", "Reintentando"
        SUCCEEDED = "succeeded", "Entregado"
        FAILED = "failed", "Fallido"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name="deliveries")
    event = models.ForeignKey(WebhookEvent, on_delete=models.CASCADE, related_name="deliveries")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    celery_task_id = models.CharField(max_length=255, blank=True, db_index=True)
    response_code = models.PositiveSmallIntegerField(null=True, blank=True)
    response_excerpt = models.CharField(max_length=500, blank=True)
    error_message = models.CharField(max_length=500, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["endpoint", "event"], name="uniq_webhook_endpoint_event")]
        indexes = [models.Index(fields=["status", "-created_at"])]
        verbose_name = "Entrega webhook"
        verbose_name_plural = "Entregas webhook"
