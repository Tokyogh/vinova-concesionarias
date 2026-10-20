#!/usr/bin/env bash
# ES: Ejecuta el flujo operativo «validate staging» con fallos controlados y sin ocultar errores.
# EN: Runs the «validate staging» operational flow with controlled failures and visible errors.
set -euo pipefail

BASE_URL="${1:-}"
ENV_FILE="${2:-.env.staging}"
RUN_SMOKE="${3:-false}"
TIMEOUT_SECONDS="${VINOVA_WAIT_TIMEOUT:-180}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

# ES: La sección siguiente define precondiciones, límites y propagación explícita de fallos.
# EN: The following section defines preconditions, limits, and explicit failure propagation.
read_env() {
  grep -E "^[[:space:]]*$1=" "$ENV_FILE" | tail -n 1 | cut -d= -f2- | tr -d '\r' || true
}
if [[ -z "$BASE_URL" ]]; then BASE_URL="$(read_env VINOVA_SMOKE_BASE_URL)"; fi
[[ -n "$BASE_URL" ]] || { echo "ERROR: falta BaseUrl/VINOVA_SMOKE_BASE_URL." >&2; exit 1; }

"$SCRIPT_DIR/staging-preflight.sh" "$ENV_FILE"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f docker-compose.prod.yml -f docker-compose.staging.yml)

app_init_id="$("${COMPOSE[@]}" ps -a -q app_init)"
[[ -n "$app_init_id" ]] || { echo "ERROR: no existe app_init; ejecute deploy-staging.sh." >&2; exit 1; }
app_init_exit="$(docker inspect --format '{{.State.ExitCode}}' "$app_init_id")"
if [[ "$app_init_exit" != "0" ]]; then
  "${COMPOSE[@]}" logs --no-color --tail=200 app_init
  echo "ERROR: app_init termino con codigo $app_init_exit." >&2
  exit 1
fi

services=(db redis web celery_worker celery_beat nginx)
deadline=$((SECONDS + TIMEOUT_SECONDS))
while true; do
  pending=()
  for service in "${services[@]}"; do
    id="$("${COMPOSE[@]}" ps -q "$service")"
    if [[ -z "$id" ]]; then pending+=("$service:no-creado"); continue; fi
    state="$(docker inspect --format '{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$id")"
    status="${state%%|*}"; health="${state#*|}"
    if [[ "$status" != "running" || ("$health" != "none" && "$health" != "healthy") ]]; then
      pending+=("$service:$state")
    fi
  done
  [[ ${#pending[@]} -eq 0 ]] && break
  if (( SECONDS >= deadline )); then
    "${COMPOSE[@]}" ps -a
    "${COMPOSE[@]}" logs --no-color --tail=150 web nginx celery_worker celery_beat
    echo "ERROR: servicios no saludables: ${pending[*]}" >&2
    exit 1
  fi
  sleep 3
done

curl_args=(--fail --silent --show-error --location)
case "$BASE_URL" in https://localhost*|https://127.0.0.1*) curl_args+=(--insecure);; esac
for path in /nginx-health /health/live/ /health/ready/; do
  curl "${curl_args[@]}" "${BASE_URL%/}$path" >/dev/null
done

"${COMPOSE[@]}" ps -a
echo "Staging saludable: app_init=0, contenedores healthy y endpoints operativos."
if [[ "$RUN_SMOKE" == "true" ]]; then "$SCRIPT_DIR/smoke-staging-read.sh" "$BASE_URL"; fi
