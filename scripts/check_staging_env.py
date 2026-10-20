#!/usr/bin/env python3
"""ES: Este módulo implementa el componente check staging env para el dominio de operación y QA.

EN: This module implements the check staging env component for the operations and QA domain.

Contexto existente / Existing context:
Operational script for check staging env.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

UNSAFE_MARKERS = re.compile(
    r"CHANGE[_-]?ME|PEGA[_-]?AQUI|example\.com|GENERATE-|PLACEHOLDER|REPLACE[_-]?ME|TODO",
    re.IGNORECASE,
)


class EnvValidationError(ValueError):
    """El archivo de entorno no es consistente para staging."""


@dataclass(frozen=True)
class ParsedEnv:
    values: dict[str, str]
    duplicates: dict[str, list[int]]


def parse_env_file(path: Path) -> ParsedEnv:
    values: dict[str, str] = {}
    occurrences: dict[str, list[int]] = {}

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise EnvValidationError(f"Linea {line_number}: se esperaba KEY=VALUE.")

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise EnvValidationError(f"Linea {line_number}: nombre de variable invalido: {key!r}.")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'\"', "'"}:
            value = value[1:-1]

        occurrences.setdefault(key, []).append(line_number)
        values[key] = value

    duplicates = {key: lines for key, lines in occurrences.items() if len(lines) > 1}
    return ParsedEnv(values=values, duplicates=duplicates)


def require(env: dict[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise EnvValidationError(f"Falta {key} o esta vacio.")
    if UNSAFE_MARKERS.search(value):
        raise EnvValidationError(f"{key} conserva un marcador sin reemplazar.")
    return value


def require_false(env: dict[str, str], key: str) -> None:
    if env.get(key, "").strip().lower() != "false":
        raise EnvValidationError(f"{key} debe ser False.")


def decode_component(value: str | None) -> str:
    return unquote(value or "")


def validate_database_url(env: dict[str, str]) -> None:
    value = require(env, "DATABASE_URL")
    parsed = urlsplit(value)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise EnvValidationError("DATABASE_URL debe usar postgres:// o postgresql://.")
    if not parsed.hostname:
        raise EnvValidationError("DATABASE_URL no contiene hostname.")

    expected_user = require(env, "POSTGRES_USER")
    expected_password = require(env, "POSTGRES_PASSWORD")
    expected_database = require(env, "POSTGRES_DB")

    if decode_component(parsed.username) != expected_user:
        raise EnvValidationError("DATABASE_URL no coincide con POSTGRES_USER.")
    if decode_component(parsed.password) != expected_password:
        raise EnvValidationError("DATABASE_URL no coincide con POSTGRES_PASSWORD.")
    if decode_component(parsed.path.lstrip("/")) != expected_database:
        raise EnvValidationError("DATABASE_URL no coincide con POSTGRES_DB.")

    profiles = {item.strip() for item in env.get("COMPOSE_PROFILES", "").split(",") if item.strip()}
    if "local-db" in profiles and parsed.hostname != "db":
        raise EnvValidationError("DATABASE_URL debe usar el host 'db' cuando COMPOSE_PROFILES incluye local-db.")


def validate_redis_url(env: dict[str, str], key: str, expected_db: int) -> None:
    value = require(env, key)
    parsed = urlsplit(value)
    if parsed.scheme not in {"redis", "rediss"}:
        raise EnvValidationError(f"{key} debe usar redis:// o rediss://.")
    if parsed.hostname != "redis":
        raise EnvValidationError(f"{key} debe usar el host 'redis' en este Compose.")

    expected_password = require(env, "REDIS_PASSWORD")
    if decode_component(parsed.password) != expected_password:
        raise EnvValidationError(f"{key} no coincide con REDIS_PASSWORD.")

    database_text = parsed.path.lstrip("/") or "0"
    try:
        database = int(database_text)
    except ValueError as exc:
        raise EnvValidationError(f"{key} contiene una base Redis invalida: {database_text!r}.") from exc
    if database != expected_db:
        raise EnvValidationError(f"{key} debe usar la base Redis {expected_db}.")


def validate_hosts(env: dict[str, str]) -> None:
    server_name = require(env, "NGINX_SERVER_NAME").lower()
    health_host = require(env, "VINOVA_HEALTHCHECK_HOST").lower()
    allowed_hosts = {item.strip().lower() for item in require(env, "ALLOWED_HOSTS").split(",") if item.strip()}
    if server_name not in allowed_hosts:
        raise EnvValidationError("NGINX_SERVER_NAME debe estar incluido en ALLOWED_HOSTS.")
    if health_host not in allowed_hosts:
        raise EnvValidationError("VINOVA_HEALTHCHECK_HOST debe estar incluido en ALLOWED_HOSTS.")

    smoke_url = require(env, "VINOVA_SMOKE_BASE_URL")
    smoke = urlsplit(smoke_url)
    if smoke.scheme != "https" or not smoke.hostname:
        raise EnvValidationError("VINOVA_SMOKE_BASE_URL debe ser una URL HTTPS valida.")
    if smoke.hostname.lower() != server_name:
        raise EnvValidationError("VINOVA_SMOKE_BASE_URL y NGINX_SERVER_NAME deben usar el mismo host.")


def validate_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise EnvValidationError(f"No existe {path}.")

    parsed = parse_env_file(path)
    if parsed.duplicates:
        detail = ", ".join(f"{key} (lineas {', '.join(map(str, lines))})" for key, lines in sorted(parsed.duplicates.items()))
        raise EnvValidationError(f"Hay variables duplicadas: {detail}.")

    env = parsed.values
    for key in (
        "SECRET_KEY",
        "VINOVA_API_TOKEN_PEPPER",
        "ALLOWED_HOSTS",
        "CSRF_TRUSTED_ORIGINS",
        "DATABASE_URL",
        "REDIS_URL",
        "CELERY_BROKER_URL",
        "CELERY_RESULT_BACKEND",
        "VINOVA_HEALTHCHECK_HOST",
        "NGINX_SERVER_NAME",
        "VINOVA_SMOKE_BASE_URL",
    ):
        require(env, key)

    require_false(env, "DEBUG")
    require_false(env, "VINOVA_API_DOCS_PUBLIC")
    require_false(env, "VINOVA_WEBHOOK_ALLOW_PRIVATE_NETWORKS")

    secret_key = require(env, "SECRET_KEY")
    token_pepper = require(env, "VINOVA_API_TOKEN_PEPPER")
    if len(secret_key) < 32 or len(token_pepper) < 32:
        raise EnvValidationError("SECRET_KEY y VINOVA_API_TOKEN_PEPPER deben tener al menos 32 caracteres.")
    if secret_key == token_pepper:
        raise EnvValidationError("SECRET_KEY y VINOVA_API_TOKEN_PEPPER deben ser distintos.")
    if len(set(secret_key)) < 8 or len(set(token_pepper)) < 8:
        raise EnvValidationError("Los secretos parecen valores de relleno y no valores aleatorios.")

    validate_database_url(env)
    validate_redis_url(env, "REDIS_URL", 0)
    validate_redis_url(env, "CELERY_BROKER_URL", 0)
    validate_redis_url(env, "CELERY_RESULT_BACKEND", 1)
    validate_hosts(env)
    return env


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Valida consistencia interna de .env.staging sin imprimir secretos.")
    parser.add_argument("--env-file", type=Path, default=Path(".env.staging"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        env = validate_env(args.env_file)
    except EnvValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        "Entorno de staging consistente: "
        f"PostgreSQL={env['POSTGRES_DB']}@db, Redis=db0/db1, host={env['NGINX_SERVER_NAME']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
