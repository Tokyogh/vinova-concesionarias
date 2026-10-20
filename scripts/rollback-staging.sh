#!/usr/bin/env bash
# ES: Ejecuta el flujo operativo «rollback staging» con fallos controlados y sin ocultar errores.
# EN: Runs the «rollback staging» operational flow with controlled failures and visible errors.
set -euo pipefail
PREVIOUS_DIR="${1:?Uso: rollback-staging.sh /ruta/release-anterior .env.staging ROLLBACK_STAGING}"
ENV_FILE="${2:-.env.staging}"
CONFIRM="${3:-}"
[[ "$CONFIRM" == "ROLLBACK_STAGING" ]] || { echo "Confirmación exacta requerida: ROLLBACK_STAGING" >&2; exit 2; }
[[ -d "$PREVIOUS_DIR" ]] || { echo "No existe el release anterior." >&2; exit 2; }
[[ -f "$PREVIOUS_DIR/docker-compose.prod.yml" ]] || { echo "Release anterior incompleto." >&2; exit 2; }
[[ -f "$ENV_FILE" ]] || { echo "No existe $ENV_FILE." >&2; exit 2; }
ENV_FILE="$(cd "$(dirname "$ENV_FILE")" && pwd)/$(basename "$ENV_FILE")"
cd "$PREVIOUS_DIR"
compose_files=(-f docker-compose.prod.yml)
[[ -f docker-compose.staging.yml ]] && compose_files+=(-f docker-compose.staging.yml)
docker compose --env-file "$ENV_FILE" "${compose_files[@]}" config --quiet
docker compose --env-file "$ENV_FILE" "${compose_files[@]}" up -d --build
printf '%s\n' "Rollback no destructivo iniciado. No se eliminaron volúmenes. Ejecute el smoke de lectura."
