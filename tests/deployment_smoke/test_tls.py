"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for tls in the deployment_smoke domain.
"""

from __future__ import annotations

from urllib.parse import urlparse

from tests.deployment_smoke.helpers.http import dns_lookup, http_redirect_url, request
from tests.deployment_smoke.helpers.runtime import run_check, skip_check
from tests.deployment_smoke.helpers.tls import inspect_certificate

__test__ = False


def run(state, session=None):  # noqa: ANN001
    config = state.config
    parsed = urlparse(config.base_url)
    run_check(
        state,
        code="network.dns",
        scenario="tls",
        title="Resolución DNS",
        callback=lambda: {"addresses": dns_lookup(config.hostname)},
        retryable=True,
    )
    if parsed.scheme != "https":
        skip_check(
            state,
            code="tls.certificate",
            scenario="tls",
            title="Certificado TLS",
            message="TLS omitido únicamente por --allow-http-local.",
            required=False,
        )
        return
    port = parsed.port or 443
    run_check(
        state,
        code="tls.certificate",
        scenario="tls",
        title="Certificado, dominio y expiración",
        callback=lambda: _tls_result(config.hostname, port, config.timeout_seconds, config.verify_tls),
        retryable=True,
    )
    run_check(
        state,
        code="http.redirect_https",
        scenario="tls",
        title="Redirección HTTP a HTTPS",
        callback=lambda: _redirect_result(config.base_url, config.timeout_seconds, config.verify_tls),
        required=config.mode == "production",
        retryable=True,
    )


def _tls_result(hostname: str, port: int, timeout: int, verify_tls: bool) -> dict:
    details = inspect_certificate(hostname, port, timeout, verify_chain=verify_tls)
    days = int(details["days_remaining"])
    if days < 0:
        raise AssertionError("El certificado TLS está vencido.")
    if days < 15:
        details.update(status="failed", message=f"El certificado vence en {days} días.")
    elif days < 30:
        details.update(status="warning", message=f"El certificado vence pronto: {days} días.")
    else:
        details.update(message=f"Certificado válido; quedan {days} días.")
    return details


def _redirect_result(base_url: str, timeout: int, verify_tls: bool) -> dict:
    http_url = http_redirect_url(base_url)
    response = request(http_url, timeout=timeout, follow_redirects=False, verify_tls=verify_tls)
    location = response.headers.get("location", "")
    if response.status not in {301, 302, 307, 308} or not location.lower().startswith("https://"):
        raise AssertionError(f"HTTP no redirigió correctamente a HTTPS: {response.status} {location!r}")
    final = request(http_url, timeout=timeout, follow_redirects=True, verify_tls=verify_tls)
    if not final.url.lower().startswith("https://") or final.status >= 400:
        raise AssertionError(f"La redirección HTTPS no terminó correctamente: {final.status} {final.url!r}")
    return {
        "status_code": response.status,
        "location": location,
        "final_url": final.url,
        "final_status": final.status,
        "elapsed_seconds": round(final.elapsed_seconds, 3),
    }
