#!/usr/bin/env bash
# ES: Ejecuta el flujo operativo «validate release» con fallos controlados y sin ocultar errores.
# EN: Runs the «validate release» operational flow with controlled failures and visible errors.
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python}"
SETTINGS="${DJANGO_TEST_SETTINGS:-config.settings.test}"
SCHEMA_OUTPUT="${VINOVA_SCHEMA_OUTPUT:-/tmp/vinova-pro-v1.0.1-openapi.yaml}"

"$PYTHON_BIN" -m ruff check .
"$PYTHON_BIN" manage.py check --settings="$SETTINGS"
"$PYTHON_BIN" manage.py makemigrations --check --dry-run --settings="$SETTINGS"
"$PYTHON_BIN" manage.py check_release_readiness --strict --settings="$SETTINGS"
"$PYTHON_BIN" manage.py spectacular --urlconf apps.api.schema_urls --validate --file "$SCHEMA_OUTPUT" --settings="$SETTINGS"
"$PYTHON_BIN" -m pytest -q

echo "Validación estática y Django/Pytest de Vinova Pro v1.0.1 completada."
echo "Esquema OpenAPI temporal: $SCHEMA_OUTPUT"
