"""ES: Este módulo centraliza validaciones contextuales para el dominio de API e integraciones.

EN: This module centralizes contextual validation for the api domain.

Contexto existente / Existing context:
Context-specific validators for the api domain.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError

RATE_LIMIT_PATTERN = re.compile(r"^[1-9][0-9]*/(s|sec|second|m|min|minute|h|hour|d|day)s?$", re.IGNORECASE)


@dataclass(frozen=True)
class ValidatedWebhookDestination:
    """ES: Destino resuelto y aprobado. EN: Resolved and approved outbound destination."""

    scheme: str
    hostname: str
    port: int
    ip_address: str


def validate_api_rate_limit(value: str) -> None:
    if not RATE_LIMIT_PATTERN.fullmatch((value or "").strip()):
        raise ValidationError(
            "Usa un límite como 60/minute, 600/hour o 5000/day."
        )


def validate_webhook_url(url: str) -> ValidatedWebhookDestination:
    """ES: Valida y resuelve una vez para fijar la conexión saliente.

    EN: Validates and resolves once so the outbound transport can pin the
    approved address and avoid a second, attacker-controlled DNS lookup.
    """

    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise ValidationError("El webhook necesita una URL HTTP o HTTPS válida.")
    if parsed.username or parsed.password:
        raise ValidationError("No se permiten credenciales embebidas en la URL del webhook.")
    if parsed.scheme != "https" and not settings.DEBUG:
        raise ValidationError("En producción los webhooks deben utilizar HTTPS.")
    allow_private = getattr(settings, "VINOVA_WEBHOOK_ALLOW_PRIVATE_NETWORKS", False)

    hostname = parsed.hostname.lower()
    if not allow_private and (hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".local")):
        raise ValidationError("No se permiten destinos webhook locales.")

    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise ValidationError("El puerto del webhook no es válido.") from exc

    addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    try:
        addresses.append(ipaddress.ip_address(hostname))
    except ValueError:
        try:
            resolved = socket.getaddrinfo(
                hostname,
                port,
                type=socket.SOCK_STREAM,
            )
            addresses.extend(ipaddress.ip_address(item[4][0]) for item in resolved)
        except socket.gaierror as exc:
            raise ValidationError("No fue posible resolver el destino webhook.") from exc

    if not addresses:
        raise ValidationError("No fue posible resolver el destino webhook.")
    unique_addresses = sorted(set(addresses), key=lambda address: (address.version, address.packed))
    if not allow_private:
        for address in unique_addresses:
            if not address.is_global:
                raise ValidationError("El destino webhook apunta a una red privada o reservada.")

    if not unique_addresses:
        raise ValidationError("No fue posible resolver el destino webhook.")
    return ValidatedWebhookDestination(
        scheme=parsed.scheme,
        hostname=hostname,
        port=port,
        ip_address=str(unique_addresses[0]),
    )
