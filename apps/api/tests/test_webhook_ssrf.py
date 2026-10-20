"""ES: Este módulo especifica regresiones ejecutables para el dominio de API e integraciones.

EN: This module specifies executable regressions for the api domain.

Contexto existente / Existing context:
Regresiones SSRF y DNS rebinding para webhooks salientes.

SSRF and DNS-rebinding regressions for outbound webhooks.
"""

from unittest.mock import Mock, patch
from urllib.request import Request

import pytest
from django.core.exceptions import ValidationError

from apps.api.validators import ValidatedWebhookDestination, validate_webhook_url
from apps.api.webhook_transport import PinnedWebhookOpener, _PinnedHTTPSConnection


def _address(ip):
    return (2, 1, 6, "", (ip, 443))


def test_webhook_rejects_dns_answer_with_any_non_global_address(settings):
    settings.VINOVA_WEBHOOK_ALLOW_PRIVATE_NETWORKS = False
    answers = [_address("93.184.216.34"), _address("127.0.0.1")]
    with patch("apps.api.validators.socket.getaddrinfo", return_value=answers):
        with pytest.raises(ValidationError, match="privada|reservada"):
            validate_webhook_url("https://hooks.example.com/events")


def test_webhook_validation_returns_the_approved_address_for_pinning(settings):
    settings.VINOVA_WEBHOOK_ALLOW_PRIVATE_NETWORKS = False
    with patch("apps.api.validators.socket.getaddrinfo", return_value=[_address("93.184.216.34")]):
        destination = validate_webhook_url("https://hooks.example.com/events")

    assert destination == ValidatedWebhookDestination(
        scheme="https",
        hostname="hooks.example.com",
        port=443,
        ip_address="93.184.216.34",
    )


def test_https_transport_connects_to_pinned_ip_but_verifies_original_hostname():
    destination = ValidatedWebhookDestination(
        scheme="https",
        hostname="hooks.example.com",
        port=443,
        ip_address="93.184.216.34",
    )
    context = Mock()
    raw_socket = Mock()
    wrapped_socket = Mock()
    context.wrap_socket.return_value = wrapped_socket
    connection = _PinnedHTTPSConnection(destination, timeout=7, context=context)

    with patch("apps.api.webhook_transport.socket.create_connection", return_value=raw_socket) as connect:
        connection.connect()

    connect.assert_called_once_with(("93.184.216.34", 443), 7, source_address=None)
    context.wrap_socket.assert_called_once_with(raw_socket, server_hostname="hooks.example.com")
    assert connection.sock is wrapped_socket


def test_pinned_transport_rejects_url_change_before_connecting():
    destination = ValidatedWebhookDestination(
        scheme="https",
        hostname="hooks.example.com",
        port=443,
        ip_address="93.184.216.34",
    )
    opener = PinnedWebhookOpener(destination)

    with pytest.raises(ValidationError, match="cambió"):
        opener.open(Request("https://other.example.com/events"))
