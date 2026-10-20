#!/usr/bin/env python3
"""ES: Este módulo implementa el componente check nginx templates para el dominio de operación y QA.

EN: This module implements the check nginx templates component for the operations and QA domain.

Contexto existente / Existing context:
Operational script for check nginx templates.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPLACEMENTS = {
    "${NGINX_SERVER_NAME}": "qa.local",
    "${NGINX_CLIENT_MAX_BODY_SIZE}": "20m",
    "${NGINX_LOGIN_RATE}": "10r/m",
    "${NGINX_LOGIN_BURST}": "10",
    "${NGINX_PROXY_READ_TIMEOUT}": "60s",
    "${NGINX_FORWARDED_PROTO}": "http",
}
HTTP2_DIRECTIVE_MIN_VERSION = (1, 25, 1)


def nginx_version() -> tuple[int, int, int]:
    result = subprocess.run(
        ["nginx", "-v"],
        check=False,
        capture_output=True,
        text=True,
    )
    output = f"{result.stdout}\n{result.stderr}"
    match = re.search(r"nginx/(\d+)\.(\d+)\.(\d+)", output)
    if result.returncode != 0 or match is None:
        raise RuntimeError(f"No se pudo determinar la versión de Nginx: {output.strip()}")
    return tuple(int(part) for part in match.groups())


def adapt_http2_syntax_for_validator(text: str, version: tuple[int, int, int]) -> str:
    """Adapta solo la copia temporal para Nginx anteriores a 1.25.1.

    La imagen productiva usa Nginx 1.30 y conserva `http2 on;`. El runtime QA
    puede incluir una versión anterior que exige el parámetro legado en listen.
    """
    if version >= HTTP2_DIRECTIVE_MIN_VERSION or "http2 on;" not in text:
        return text

    listen_pattern = re.compile(r"(?m)^(\s*listen\s+8443\s+ssl)(\s*;\s*)$")
    adapted, replacements = listen_pattern.subn(r"\1 http2\2", text)
    if replacements == 0:
        raise RuntimeError(
            "La plantilla usa 'http2 on;' pero no se encontró 'listen 8443 ssl;' "
            "para adaptar el chequeo con Nginx antiguo."
        )
    adapted = re.sub(r"(?m)^\s*http2\s+on;\s*\n?", "", adapted)
    return adapted


def render(
    template: Path,
    *,
    cert: Path | None = None,
    key: Path | None = None,
    validator_version: tuple[int, int, int],
) -> str:
    text = template.read_text(encoding="utf-8")
    for source, target in REPLACEMENTS.items():
        text = text.replace(source, target)
    if cert and key:
        text = text.replace("${NGINX_SSL_CERTIFICATE}", str(cert))
        text = text.replace("${NGINX_SSL_CERTIFICATE_KEY}", str(key))
    text = text.replace("server web:8000;", "server 127.0.0.1:8000;")
    text = text.replace("access_log /var/log/nginx/access.log", "access_log logs/access.log")
    return adapt_http2_syntax_for_validator(text, validator_version)


def validate(
    template_name: str,
    *,
    https: bool,
    validator_version: tuple[int, int, int],
) -> None:
    """ES: Valida y normaliza «validate» antes de permitir efectos en operación y QA.

    EN: Validates and normalizes «validate» before allowing effects in operations and QA.
    """

    with tempfile.TemporaryDirectory(prefix="vinova-nginx-") as temp_name:
        temp = Path(temp_name)
        (temp / "conf.d").mkdir()
        (temp / "logs").mkdir()
        runtime = temp / "runtime"
        for name in ("client_body", "proxy", "fastcgi", "uwsgi", "scgi"):
            (runtime / name).mkdir(parents=True, exist_ok=True)

        cert = key = None
        if https:
            cert = temp / "qa.crt"
            key = temp / "qa.key"
            subprocess.run(
                [
                    "openssl",
                    "req",
                    "-x509",
                    "-newkey",
                    "rsa:2048",
                    "-nodes",
                    "-days",
                    "1",
                    "-subj",
                    "/CN=qa.local",
                    "-keyout",
                    str(key),
                    "-out",
                    str(cert),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        rendered = render(
            ROOT / "docker" / "nginx" / "templates" / template_name,
            cert=cert,
            key=key,
            validator_version=validator_version,
        )
        (temp / "conf.d" / "default.conf").write_text(rendered, encoding="utf-8")
        (temp / "nginx.conf").write_text(
            "worker_processes 1;\n"
            "pid logs/nginx.pid;\n"
            "error_log logs/error.log;\n"
            "events { worker_connections 64; }\n"
            "http {\n"
            "    client_body_temp_path runtime/client_body;\n"
            "    proxy_temp_path runtime/proxy;\n"
            "    fastcgi_temp_path runtime/fastcgi;\n"
            "    uwsgi_temp_path runtime/uwsgi;\n"
            "    scgi_temp_path runtime/scgi;\n"
            "    include /etc/nginx/mime.types;\n"
            "    include conf.d/*.conf;\n"
            "}\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            ["nginx", "-t", "-p", f"{temp}/", "-c", "nginx.conf"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError((result.stdout + "\n" + result.stderr).strip())


def main() -> int:
    missing = [tool for tool in ("nginx", "openssl") if shutil.which(tool) is None]
    if missing:
        raise RuntimeError(f"Herramientas ausentes: {', '.join(missing)}")

    version = nginx_version()
    version_text = ".".join(str(part) for part in version)
    if version < HTTP2_DIRECTIVE_MIN_VERSION:
        print(
            f"Nginx QA {version_text}: usando sintaxis HTTP/2 compatible solo "
            "en la copia temporal de validación."
        )

    validate("http.conf.template", https=False, validator_version=version)
    validate("https.conf.template", https=True, validator_version=version)
    print("Plantillas Nginx HTTP y HTTPS válidas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
