"""ES: Este módulo implementa el componente webhook transport para el dominio de API e integraciones.

EN: This module implements the webhook transport component for the api domain.

Contexto existente / Existing context:
Transporte de webhooks con destino DNS fijado y TLS verificado.

Webhook transport with a pinned DNS destination and verified TLS identity.
"""

from __future__ import annotations

import http.client
import socket
import ssl
from urllib.parse import urlsplit, urlunsplit

from django.core.exceptions import ValidationError

from apps.api.validators import ValidatedWebhookDestination


class _PinnedHTTPConnection(http.client.HTTPConnection):
    """ES: Conecta a la IP aprobada. EN: Connects to the approved IP address."""

    def __init__(self, destination: ValidatedWebhookDestination, *, timeout: float):
        super().__init__(destination.hostname, destination.port, timeout=timeout)
        self.destination = destination

    def connect(self):
        self.sock = socket.create_connection(
            (self.destination.ip_address, self.destination.port),
            self.timeout,
            source_address=self.source_address,
        )


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """ES: Fija IP conservando SNI/certificado. EN: Pins IP while preserving SNI/certificate checks."""

    def __init__(self, destination: ValidatedWebhookDestination, *, timeout: float, context=None):
        super().__init__(destination.hostname, destination.port, timeout=timeout, context=context)
        self.destination = destination

    def connect(self):
        raw_socket = socket.create_connection(
            (self.destination.ip_address, self.destination.port),
            self.timeout,
            source_address=self.source_address,
        )
        try:
            self.sock = self._context.wrap_socket(raw_socket, server_hostname=self.destination.hostname)
        except Exception:
            raw_socket.close()
            raise


class _PinnedResponse:
    """ES: Cierra respuesta y conexión. EN: Closes both response and connection."""

    def __init__(self, response, connection):
        self.response = response
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
        return False

    def getcode(self):
        return self.response.status

    def read(self, size=-1):
        return self.response.read(size)

    def close(self):
        try:
            self.response.close()
        finally:
            self.connection.close()


class PinnedWebhookOpener:
    """ES: Envía sin proxy ni redirección. EN: Sends without proxies or redirects."""

    def __init__(self, destination: ValidatedWebhookDestination):
        self.destination = destination

    def open(self, request, timeout=10):
        parsed = urlsplit(request.full_url)
        request_port = parsed.port or (443 if parsed.scheme == "https" else 80)
        expected = self.destination
        if (
            parsed.scheme != expected.scheme
            or (parsed.hostname or "").lower() != expected.hostname
            or request_port != expected.port
        ):
            raise ValidationError("El destino del webhook cambió después de validarse.")

        if expected.scheme == "https":
            connection = _PinnedHTTPSConnection(
                expected,
                timeout=timeout,
                context=ssl.create_default_context(),
            )
        else:
            connection = _PinnedHTTPConnection(expected, timeout=timeout)

        path = urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
        headers = dict(request.header_items())
        headers["Host"] = parsed.netloc
        try:
            connection.request(request.get_method(), path, body=request.data, headers=headers)
            return _PinnedResponse(connection.getresponse(), connection)
        except Exception:
            connection.close()
            raise
