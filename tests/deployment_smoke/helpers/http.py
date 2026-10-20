"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for http in the deployment_smoke helpers domain.
"""

from __future__ import annotations

import socket
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse


@dataclass
class HttpResponse:
    url: str
    status: int
    headers: dict[str, str]
    body: bytes
    elapsed_seconds: float

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def dns_lookup(hostname: str) -> list[str]:
    addresses = {item[4][0] for item in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)}
    return sorted(addresses)


def request(
    url: str,
    *,
    timeout: int,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    follow_redirects: bool = True,
    verify_tls: bool = True,
) -> HttpResponse:
    request_headers = {"User-Agent": "Vinova-Deployment-Smoke/1.0", **(headers or {})}
    req = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    handlers: list[object] = []
    if not follow_redirects:
        handlers.append(NoRedirect())
    # El opener debe conocer la política TLS aunque la URL inicial sea HTTP:
    # una redirección puede terminar en HTTPS. Sin este handler, urllib usa el
    # contexto global y vuelve a rechazar el certificado local autofirmado.
    context = ssl.create_default_context() if verify_tls else ssl._create_unverified_context()
    handlers.append(urllib.request.HTTPSHandler(context=context))
    opener = urllib.request.build_opener(*handlers)
    started = time.monotonic()
    try:
        with opener.open(req, timeout=timeout) as response:
            body = response.read(2_000_000)
            return HttpResponse(
                url=response.geturl(),
                status=int(response.status),
                headers={key.lower(): value for key, value in response.headers.items()},
                body=body,
                elapsed_seconds=time.monotonic() - started,
            )
    except urllib.error.HTTPError as exc:
        body = exc.read(2_000_000)
        return HttpResponse(
            url=exc.geturl(),
            status=int(exc.code),
            headers={key.lower(): value for key, value in exc.headers.items()},
            body=body,
            elapsed_seconds=time.monotonic() - started,
        )


def absolute(base_url: str, path: str) -> str:
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def http_redirect_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    netloc = parsed.hostname or ""
    if parsed.port and parsed.port not in {80, 443}:
        netloc = f"{netloc}:{parsed.port}"
    return parsed._replace(scheme="http", netloc=netloc, path="/", params="", query="", fragment="").geturl()


def default_ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context()
