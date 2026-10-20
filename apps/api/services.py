"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de API e integraciones.

EN: This module implements business services and transactional effects for the api domain.

Contexto existente / Existing context:
Transactional business services for the api domain.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.api.models import APIClient, IdempotencyRecord, IntegrationLog, WebhookDelivery, WebhookEndpoint, WebhookEvent
from apps.audit.services import sanitize_payload
from apps.common.logging import redact_sensitive
from apps.security_center.crypto import decrypt_secret, encrypt_secret


def canonical_json(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")


def sha256_payload(value) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def issue_api_client_token(client: APIClient, *, actor=None) -> str:
    token = client.issue_token()
    if actor:
        client.rotated_by = actor
        client.save(update_fields=["rotated_by", "updated_at"])
    log_integration(
        direction=IntegrationLog.Direction.INTERNAL,
        category="api_client",
        action="api_client.secret.rotated",
        status=IntegrationLog.Status.SUCCESS,
        client=client,
        user=actor,
        branch=client.branch,
    )
    return token


def issue_webhook_secret(endpoint: WebhookEndpoint, *, actor=None) -> str:
    raw = secrets.token_urlsafe(36)
    endpoint.encrypted_secret = encrypt_secret(raw)
    endpoint.secret_last_four = raw[-4:]
    endpoint.rotated_at = timezone.now()
    endpoint.save(update_fields=["encrypted_secret", "secret_last_four", "rotated_at", "updated_at"])
    log_integration(
        direction=IntegrationLog.Direction.INTERNAL,
        category="webhook",
        action="webhook.secret.rotated",
        status=IntegrationLog.Status.SUCCESS,
        user=actor,
        branch=endpoint.branch,
        metadata={"endpoint_id": str(endpoint.public_id)},
    )
    return raw


def webhook_signature(endpoint: WebhookEndpoint, body: bytes, timestamp: str) -> str:
    secret = decrypt_secret(endpoint.encrypted_secret)
    if not secret:
        raise ValidationError("El endpoint no dispone de un secreto de firma válido.")
    signed = f"{timestamp}.".encode("utf-8") + body
    return hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()


def log_integration(*, direction, category, action, status, client=None, user=None, branch=None, request_id=None,
                    endpoint="", http_method="", http_status=None, duration_ms=None, payload=None,
                    idempotency_key_hash="", error_code="", error_message="", metadata=None):
    return IntegrationLog.objects.create(
        direction=direction,
        category=category,
        action=action,
        status=status,
        client=client,
        user=user if getattr(user, "is_authenticated", False) else None,
        branch=branch,
        request_id=request_id,
        endpoint=endpoint[:500],
        http_method=http_method[:12],
        http_status=http_status,
        duration_ms=duration_ms,
        payload_hash=sha256_payload(payload) if payload is not None else "",
        idempotency_key_hash=idempotency_key_hash,
        error_code=error_code[:80],
        error_message=redact_sensitive(error_message)[:500],
        metadata=sanitize_payload(metadata or {}),
    )


def begin_idempotency(*, client: APIClient, key: str, method: str, path: str, payload):
    """ES: Ejecuta la operación «begin idempotency» dentro del dominio de API e integraciones. Además, conserva atomicidad y bloqueos explícitos, rechaza estados o entradas inválidas.

    EN: Executes the «begin idempotency» operation within the api domain. It also preserves atomicity and explicit locking, rejects invalid input or state.
    """

    if not key or len(key) > 200:
        raise ValidationError("Envía un encabezado Idempotency-Key de hasta 200 caracteres.")
    key_hash = hashlib.sha256(f"{client.public_id}:{key}".encode("utf-8")).hexdigest()
    request_hash = sha256_payload(payload)
    now = timezone.now()
    expires_at = now + timedelta(hours=getattr(settings, "VINOVA_IDEMPOTENCY_TTL_HOURS", 24))
    defaults = {
        "key_hint": f"…{key[-8:]}",
        "method": method,
        "path": path,
        "request_hash": request_hash,
        "expires_at": expires_at,
    }
    with transaction.atomic():
        # get_or_create handles the unique-key race and select_for_update locks an
        # existing record before its state is evaluated or reset.
        record, created = IdempotencyRecord.objects.select_for_update().get_or_create(
            client=client,
            key_hash=key_hash,
            defaults=defaults,
        )
        if created:
            return record, False

        active = record.expires_at > now
        same_request = (
            record.request_hash == request_hash
            and record.method == method
            and record.path == path
        )
        if active and not same_request:
            raise ValidationError("La misma Idempotency-Key fue utilizada con una solicitud diferente.")
        if active and record.status == IdempotencyRecord.Status.COMPLETED:
            return record, True
        if active and record.status == IdempotencyRecord.Status.PROCESSING:
            raise ValidationError("La solicitud con esta Idempotency-Key todavía se está procesando.")

        # Failed records may retry the same request immediately. Expired records
        # may be reused, including with a new payload, according to the TTL.
        record.key_hint = f"…{key[-8:]}"
        record.method = method
        record.path = path
        record.request_hash = request_hash
        record.status = IdempotencyRecord.Status.PROCESSING
        record.expires_at = expires_at
        record.response_status = None
        record.response_body = {}
        record.completed_at = None
        record.save(
            update_fields=[
                "key_hint",
                "method",
                "path",
                "request_hash",
                "status",
                "expires_at",
                "response_status",
                "response_body",
                "completed_at",
                "updated_at",
            ]
        )
        return record, False


def complete_idempotency(record: IdempotencyRecord, *, response_status: int, response_body: dict):
    record.status = IdempotencyRecord.Status.COMPLETED
    record.response_status = response_status
    record.response_body = sanitize_payload(response_body)
    record.completed_at = timezone.now()
    record.save(update_fields=["status", "response_status", "response_body", "completed_at", "updated_at"])


def fail_idempotency(record: IdempotencyRecord):
    record.status = IdempotencyRecord.Status.FAILED
    record.save(update_fields=["status", "updated_at"])


def publish_webhook_event(*, event_type: str, aggregate_type: str = "", aggregate_id: str = "", branch=None, payload=None):
    from django.db import models

    queryset = WebhookEndpoint.objects.filter(is_active=True).exclude(encrypted_secret="")
    if branch:
        queryset = queryset.filter(models.Q(branch__isnull=True) | models.Q(branch=branch))
    endpoints = [endpoint for endpoint in queryset if endpoint.subscribes_to(event_type)]
    if not endpoints:
        return None
    safe_payload = sanitize_payload(payload or {})
    event = WebhookEvent.objects.create(
        event_type=event_type,
        aggregate_type=aggregate_type[:80],
        aggregate_id=str(aggregate_id)[:100],
        branch=branch,
        payload=safe_payload,
    )
    deliveries = [WebhookDelivery(endpoint=endpoint, event=event) for endpoint in endpoints]
    WebhookDelivery.objects.bulk_create(deliveries)

    def dispatch():
        from apps.api.tasks import deliver_webhook_task

        for delivery in WebhookDelivery.objects.filter(event=event, status=WebhookDelivery.Status.PENDING):
            try:
                result = deliver_webhook_task.apply_async(args=[delivery.pk], queue=getattr(settings, "CELERY_WEBHOOK_QUEUE", "webhooks"))
                WebhookDelivery.objects.filter(pk=delivery.pk).update(celery_task_id=result.id)
            except Exception as exc:
                safe_error = redact_sensitive(exc)[:500]
                WebhookDelivery.objects.filter(pk=delivery.pk).update(
                    status=WebhookDelivery.Status.FAILED,
                    error_message=safe_error,
                )
                log_integration(
                    direction=IntegrationLog.Direction.OUTBOUND,
                    category="webhook",
                    action="webhook.enqueue",
                    status=IntegrationLog.Status.FAILED,
                    branch=event.branch,
                    endpoint=delivery.endpoint.url,
                    error_code="publish_failed",
                    error_message=safe_error,
                    metadata={"event_id": str(event.event_id), "delivery_id": str(delivery.public_id)},
                )

    transaction.on_commit(dispatch)
    return event
