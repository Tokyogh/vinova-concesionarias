#!/usr/bin/env bash
# ES: Ejecuta el flujo operativo «qa deployment smoke» con fallos controlados y sin ocultar errores.
# EN: Runs the «qa deployment smoke» operational flow with controlled failures and visible errors.
set -Eeuo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"
PYTHON_BIN="${VINOVA_SMOKE_PYTHON:-python3}"
exec "$PYTHON_BIN" scripts/run_deployment_smoke.py "$@"
