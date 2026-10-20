#!/usr/bin/env bash
# ES: Ejecuta el flujo operativo «smoke staging write» con fallos controlados y sin ocultar errores.
# EN: Runs the «smoke staging write» operational flow with controlled failures and visible errors.
set -euo pipefail
BASE_URL="${1:?Uso: smoke-staging-write.sh https://staging.example.com CONFIRM_WRITE}"
CONFIRM="${2:-}"
[[ "$CONFIRM" == "CONFIRM_WRITE" ]] || { echo "Se requiere CONFIRM_WRITE." >&2; exit 2; }
[[ "${VINOVA_SMOKE_ALLOW_WRITE:-}" == "true" ]] || { echo "Defina VINOVA_SMOKE_ALLOW_WRITE=true." >&2; exit 2; }
[[ -n "${VINOVA_SMOKE_USERNAME:-}" && -n "${VINOVA_SMOKE_PASSWORD:-}" ]] || { echo "Faltan credenciales smoke." >&2; exit 2; }
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TLS_ARGS=()
[[ "$BASE_URL" =~ ^https://(localhost|127\.0\.0\.1|\[::1\])([:/]|$) ]] && TLS_ARGS+=(--insecure-local-tls)
"$SCRIPT_DIR/qa-deployment-smoke.sh" "$BASE_URL" \
  --mode staging "${TLS_ARGS[@]}" --write-tests --cleanup \
  --scenario public --scenario auth --scenario health --scenario navigation --scenario security \
  --scenario customers --scenario vehicles --scenario inventory --scenario sales \
  --scenario documents --scenario accessibility --scenario cleanup \
  --timeout "${VINOVA_SMOKE_TIMEOUT:-30}" --retries "${VINOVA_SMOKE_RETRIES:-0}"
