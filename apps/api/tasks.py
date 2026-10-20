"""ES: Este módulo expone tareas asíncronas y sus límites operativos para el dominio de API e integraciones.

EN: This module exposes asynchronous tasks and their operational limits for the api domain.

Contexto existente / Existing context:
Asynchronous task entry points for the api domain.
"""

from __future__ import annotations

import time
from datetime import timedelta
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import Request

from celery import shared_task
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.api.models import IntegrationLog, WebhookDelivery
from apps.api.services import canonical_json, log_integration, webhook_signature
from apps.api.validators import validate_webhook_url
from apps.api.webhook_transport import PinnedWebhookOpener
from apps.common.logging import redact_sensitive


def _webhook_opener(destination):
    return PinnedWebhookOpener(destination)


@shared_task(bind=True, max_retries=10, default_retry_delay=30)
def deliver_webhook_task(self, delivery_id: int):
    """Deliver one persisted webhook with retry and endpoint safety controls."""

    delivery = WebhookDelivery.objects.select_related("endpoint", "event", "event__branch").get(pk=delivery_id)
    endpoint = delivery.endpoint
    event = delivery.event
    if not endpoint.is_active:
        delivery.status = WebhookDelivery.Status.FAILED
        delivery.error_message = "Endpoint inactivo."
        delivery.save(update_fields=["status", "error_message", "updated_at"])
        return {"status": "inactive"}

    delivery.status = WebhookDelivery.Status.SENDING
    delivery.attempts += 1
    delivery.error_message = ""
    delivery.save(update_fields=["status", "attempts", "error_message", "updated_at"])
    envelope = {
        "id": str(event.event_id),
        "type": event.event_type,
        "occurred_at": event.occurred_at.isoformat(),
        "data": event.payload,
    }
    body = canonical_json(envelope)
    timestamp = str(int(time.time()))
    started = time.monotonic()
    try:
        destination = validate_webhook_url(endpoint.url)
        signature = webhook_signature(endpoint, body, timestamp)
        request = Request(
            endpoint.url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Vinova-Pro-Webhooks/1.0",
                "X-Vinova-Event": event.event_type,
                "X-Vinova-Delivery": str(delivery.public_id),
                "X-Vinova-Timestamp": timestamp,
                "X-Vinova-Signature": f"v1={signature}",
            },
        )
        with _webhook_opener(destination).open(
            request,
            timeout=min(max(endpoint.timeout_seconds, 2), 30),
        ) as response:
            code = response.getcode()
            excerpt = redact_sensitive(response.read(500).decode("utf-8", errors="replace"))
        if code < 200 or code >= 300:
            raise HTTPError(endpoint.url, code, "Respuesta no exitosa", hdrs=None, fp=None)

        delivery.status = WebhookDelivery.Status.SUCCEEDED
        delivery.response_code = code
        delivery.response_excerpt = excerpt[:500]
        delivery.delivered_at = timezone.now()
        delivery.next_retry_at = None
        delivery.save(
            update_fields=[
                "status",
                "response_code",
                "response_excerpt",
                "delivered_at",
                "next_retry_at",
                "updated_at",
            ]
        )
        endpoint.last_success_at = timezone.now()
        endpoint.save(update_fields=["last_success_at", "updated_at"])
        log_integration(
            direction=IntegrationLog.Direction.OUTBOUND,
            category="webhook",
            action=event.event_type,
            status=IntegrationLog.Status.SUCCESS,
            branch=event.branch,
            endpoint=endpoint.url,
            http_method="POST",
            http_status=code,
            duration_ms=int((time.monotonic() - started) * 1000),
            payload=envelope,
            metadata={
                "event_id": str(event.event_id),
                "delivery_id": str(delivery.public_id),
                "attempt": delivery.attempts,
            },
        )
        return {"status": "succeeded", "code": code}
    except (HTTPError, HTTPException, URLError, TimeoutError, ValidationError, OSError) as exc:
        code = getattr(exc, "code", None)
        endpoint.last_failure_at = timezone.now()
        endpoint.save(update_fields=["last_failure_at", "updated_at"])
        can_retry = delivery.attempts < min(endpoint.max_retries, self.max_retries)
        delivery.response_code = code if isinstance(code, int) else None
        delivery.error_message = redact_sensitive(exc)[:500]
        delivery.status = WebhookDelivery.Status.RETRYING if can_retry else WebhookDelivery.Status.FAILED
        countdown = min(30 * (2 ** max(delivery.attempts - 1, 0)), 1800)
        delivery.next_retry_at = timezone.now() + timedelta(seconds=countdown) if can_retry else None
        delivery.save(
            update_fields=[
                "status",
                "response_code",
                "error_message",
                "next_retry_at",
                "updated_at",
            ]
        )
        log_integration(
            direction=IntegrationLog.Direction.OUTBOUND,
            category="webhook",
            action=event.event_type,
            status=IntegrationLog.Status.PENDING if can_retry else IntegrationLog.Status.FAILED,
            branch=event.branch,
            endpoint=endpoint.url,
            http_method="POST",
            http_status=delivery.response_code,
            duration_ms=int((time.monotonic() - started) * 1000),
            payload=envelope,
            error_code="delivery_retry" if can_retry else "delivery_failed",
            error_message=exc,
            metadata={
                "event_id": str(event.event_id),
                "delivery_id": str(delivery.public_id),
                "attempt": delivery.attempts,
            },
        )
        if can_retry:
            raise self.retry(exc=exc, countdown=countdown)
        return {"status": "failed", "error": str(exc)[:200]}
