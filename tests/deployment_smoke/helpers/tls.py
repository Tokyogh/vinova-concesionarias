"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for tls in the deployment_smoke helpers domain.
"""

from __future__ import annotations

import ipaddress
import socket
import ssl
from datetime import UTC, datetime

from cryptography import x509


def _dns_matches(pattern: str, hostname: str) -> bool:
    pattern_labels = pattern.rstrip(".").lower().split(".")
    hostname_labels = hostname.rstrip(".").lower().split(".")
    if "*" not in pattern:
        return pattern_labels == hostname_labels
    return (
        len(pattern_labels) == len(hostname_labels)
        and pattern_labels[0] == "*"
        and all("*" not in label for label in pattern_labels[1:])
        and pattern_labels[1:] == hostname_labels[1:]
    )


def _verify_hostname(certificate: x509.Certificate, hostname: str) -> None:
    dns_names: list[str] = []
    ip_names: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    try:
        san = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        dns_names = san.get_values_for_type(x509.DNSName)
        ip_names = san.get_values_for_type(x509.IPAddress)
    except x509.ExtensionNotFound:
        pass

    try:
        target_ip = ipaddress.ip_address(hostname)
    except ValueError:
        target_ip = None

    if target_ip is not None:
        if target_ip not in ip_names:
            raise ssl.CertificateError(f"El certificado TLS no incluye la IP {hostname}.")
        return

    candidates = dns_names
    if not candidates:
        candidates = [
            item.value
            for item in certificate.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
        ]
    if not any(_dns_matches(candidate, hostname) for candidate in candidates):
        raise ssl.CertificateError(
            f"El certificado TLS no coincide con {hostname}; nombres: {', '.join(candidates) or 'ninguno'}."
        )


def inspect_certificate(
    hostname: str,
    port: int,
    timeout: int,
    *,
    verify_chain: bool = True,
) -> dict[str, object]:
    context = ssl.create_default_context() if verify_chain else ssl._create_unverified_context()
    with socket.create_connection((hostname, port), timeout=timeout) as raw_socket:
        with context.wrap_socket(raw_socket, server_hostname=hostname) as secure_socket:
            certificate_der = secure_socket.getpeercert(binary_form=True)
            cipher = secure_socket.cipher()
            protocol = secure_socket.version()

    if not certificate_der:
        raise RuntimeError("No se pudo obtener el certificado TLS remoto.")

    certificate = x509.load_der_x509_certificate(certificate_der)
    _verify_hostname(certificate, hostname)
    expires_at = certificate.not_valid_after_utc
    days_remaining = int((expires_at - datetime.now(UTC)).total_seconds() // 86400)
    return {
        "subject": certificate.subject.rfc4514_string(),
        "issuer": certificate.issuer.rfc4514_string(),
        "serial_number": format(certificate.serial_number, "x"),
        "expires_at": expires_at.isoformat(),
        "days_remaining": days_remaining,
        "protocol": protocol,
        "cipher": cipher[0] if cipher else "",
        "chain_verified": verify_chain,
    }
