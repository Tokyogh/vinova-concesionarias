#!/usr/bin/env bash
# ES: Ejecuta el flujo operativo «smoke staging read» con fallos controlados y sin ocultar errores.
# EN: Runs the «smoke staging read» operational flow with controlled failures and visible errors.
set -euo pipefail
BASE_URL="${1:?Uso: smoke-staging-read.sh https://staging.example.com}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TLS_ARGS=()
[[ "$BASE_URL" =~ ^https://(localhost|127\.0\.0\.1|\[::1\])([:/]|$) ]] && TLS_ARGS+=(--insecure-local-tls)
"$SCRIPT_DIR/qa-deployment-smoke.sh" "$BASE_URL" \
  --mode staging "${TLS_ARGS[@]}" \
  --scenario tls --scenario public --scenario auth --scenario health \
  --scenario assets --scenario navigation --scenario security --scenario accessibility \
  --timeout "${VINOVA_SMOKE_TIMEOUT:-30}" --retries "${VINOVA_SMOKE_RETRIES:-1}"
