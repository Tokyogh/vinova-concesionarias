#!/usr/bin/env bash
# ES: Ejecuta el flujo operativo «deploy staging» con fallos controlados y sin ocultar errores.
# EN: Runs the «deploy staging» operational flow with controlled failures and visible errors.
set -euo pipefail

ENV_FILE="${1:-.env.staging}"
SKIP_BUILD="${2:-false}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

"$SCRIPT_DIR/staging-preflight.sh" "$ENV_FILE"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f docker-compose.prod.yml -f docker-compose.staging.yml)

if [[ "$SKIP_BUILD" != "true" ]]; then
  "${COMPOSE[@]}" build --pull
fi

if ! "${COMPOSE[@]}" up -d; then
  "${COMPOSE[@]}" ps -a || true
  "${COMPOSE[@]}" logs --no-color --tail=200 db redis app_init || true
  echo "ERROR: fallo el arranque de staging; revise los logs anteriores." >&2
  exit 1
fi

"${COMPOSE[@]}" ps -a
printf '%s\n' "Staging iniciado. Continue con validate-staging.sh."
