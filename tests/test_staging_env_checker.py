"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for staging env checker in the project domain.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.check_staging_env import EnvValidationError, validate_env


def valid_env() -> str:
    return """\
COMPOSE_PROFILES=local-db
SECRET_KEY=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ123456
VINOVA_API_TOKEN_PEPPER=9876543210abcdefghijklmnopqrstuvwxyzABCDEFGH
DEBUG=False
VINOVA_API_DOCS_PUBLIC=False
VINOVA_WEBHOOK_ALLOW_PRIVATE_NETWORKS=False
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://localhost
VINOVA_HEALTHCHECK_HOST=localhost
NGINX_SERVER_NAME=localhost
VINOVA_SMOKE_BASE_URL=https://localhost
POSTGRES_DB=vinova_pro_staging
POSTGRES_USER=vinova_staging
POSTGRES_PASSWORD=postgres-secret
DATABASE_URL=postgres://vinova_staging:postgres-secret@db:5432/vinova_pro_staging
REDIS_PASSWORD=redis-secret
REDIS_URL=redis://:redis-secret@redis:6379/0
CELERY_BROKER_URL=redis://:redis-secret@redis:6379/0
CELERY_RESULT_BACKEND=redis://:redis-secret@redis:6379/1
"""


def write_env(tmp_path: Path, content: str) -> Path:
    path = tmp_path / ".env.staging"
    path.write_text(content, encoding="utf-8")
    return path


def test_valid_staging_env_is_accepted(tmp_path: Path) -> None:
    env = validate_env(write_env(tmp_path, valid_env()))
    assert env["POSTGRES_DB"] == "vinova_pro_staging"


def test_placeholder_inside_database_url_is_rejected(tmp_path: Path) -> None:
    content = valid_env().replace("postgres-secret@db", "PEGA_AQUI@db")
    with pytest.raises(EnvValidationError, match="marcador"):
        validate_env(write_env(tmp_path, content))


def test_duplicate_variables_are_rejected(tmp_path: Path) -> None:
    content = valid_env() + "\nREDIS_PASSWORD=another-value\n"
    with pytest.raises(EnvValidationError, match="duplicadas"):
        validate_env(write_env(tmp_path, content))


def test_redis_password_mismatch_is_rejected(tmp_path: Path) -> None:
    content = valid_env().replace("REDIS_URL=redis://:redis-secret", "REDIS_URL=redis://:other-secret")
    with pytest.raises(EnvValidationError, match="REDIS_PASSWORD"):
        validate_env(write_env(tmp_path, content))
