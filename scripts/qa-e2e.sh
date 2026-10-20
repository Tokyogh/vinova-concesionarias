#!/usr/bin/env bash
# ES: Ejecuta el flujo operativo «qa e2e» con fallos controlados y sin ocultar errores.
# EN: Runs the «qa e2e» operational flow with controlled failures and visible errors.
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_NAME="${VINOVA_QA_PROJECT_NAME:-vinova-qa-cli}"
COMPOSE=(docker compose --project-name "$PROJECT_NAME" -f "$PROJECT_ROOT/docker-compose.qa-cli.yml")
REPORTS="$PROJECT_ROOT/private/qa_reports"
RUN_NAME="e2e-targeted-$(date +%Y%m%d-%H%M%S)"
HOST_OUTPUT="$REPORTS/$RUN_NAME"
OUTPUT="/app/private/qa_reports/$RUN_NAME"
BROWSER="chromium"
REBUILD=0
FAIL_FAST="auto"
SCENARIOS=()
ALLOWED=" public auth vehicles customers inventory sales documents security roles accessibility portal all "

# ES: La sección siguiente define precondiciones, límites y propagación explícita de fallos.
# EN: The following section defines preconditions, limits, and explicit failure propagation.
after_failure() {
  local phase="$1" message="$2" code="${3:-1}"
  mkdir -p "$HOST_OUTPUT"
  python - "$HOST_OUTPUT/summary.json" "$phase" "$message" "$code" "$BROWSER" "${SCENARIOS[*]:-all}" <<'PY'
import json, sys
from pathlib import Path
path, phase, message, code, browser, scenarios = sys.argv[1:]
payload = {"schema_version": 1, "status": "failed", "phase": phase, "environment": "shell-host-wrapper", "requested_scenarios": scenarios.split(), "browser": browser, "exit_code": int(code), "message": message}
Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
PY
  echo "Resumen de error: $HOST_OUTPUT/summary.json" >&2
}

while (($#)); do
  case "$1" in
    --browser) shift; BROWSER="${1:-}" ;;
    --rebuild) REBUILD=1 ;;
    --fail-fast) FAIL_FAST=1 ;;
    --no-fail-fast) FAIL_FAST=0 ;;
    chromium|firefox|webkit) BROWSER="$1" ;;
    *,*) after_failure argument-validation "No uses listas con comas; separa los escenarios con espacios." 2; exit 2 ;;
    test_01) SCENARIOS+=(public) ;;
    test_02) SCENARIOS+=(auth) ;;
    test_03) SCENARIOS+=(vehicles) ;;
    test_04) SCENARIOS+=(customers) ;;
    test_05) SCENARIOS+=(inventory) ;;
    test_06) SCENARIOS+=(sales) ;;
    test_07) SCENARIOS+=(documents) ;;
    test_08) SCENARIOS+=(security) ;;
    test_09) SCENARIOS+=(roles) ;;
    test_10) SCENARIOS+=(accessibility) ;;
    test_11) SCENARIOS+=(portal) ;;
    *)
      if [[ "$ALLOWED" != *" $1 "* ]]; then
        after_failure argument-validation "Escenario E2E no permitido: $1" 2
        exit 2
      fi
      SCENARIOS+=("$1")
      ;;
  esac
  shift || true
done

((${#SCENARIOS[@]})) || SCENARIOS=(all)
if ((${#SCENARIOS[@]} > 1)) && [[ " ${SCENARIOS[*]} " == *" all "* ]]; then
  after_failure argument-validation "Usa all solo o varios escenarios concretos." 2
  exit 2
fi
[[ "$FAIL_FAST" != auto ]] || { [[ "${SCENARIOS[0]}" == all ]] && FAIL_FAST=0 || FAIL_FAST=1; }

mkdir -p "$REPORTS"
cd "$PROJECT_ROOT"
cleanup() { "${COMPOSE[@]}" down --remove-orphans >/dev/null 2>&1 || true; }
trap cleanup EXIT

docker info >/dev/null || { after_failure docker-info "Docker no esta iniciado." 1; exit 1; }
"${COMPOSE[@]}" config --quiet || { after_failure compose-validation "Compose QA no es valido." 1; exit 1; }
IMAGE_ID="$("${COMPOSE[@]}" images -q qa_runner 2>/dev/null | head -n1 || true)"
if ((REBUILD)) || [[ -z "$IMAGE_ID" ]]; then
  "${COMPOSE[@]}" build qa_runner || { after_failure image-preparation "No se pudo construir la imagen QA." 1; exit 1; }
else
  echo "Reutilizando la imagen QA existente."
fi
"${COMPOSE[@]}" up -d --wait qa_db qa_redis || { "${COMPOSE[@]}" logs --tail=120 qa_db qa_redis || true; after_failure infrastructure-start "No se pudo iniciar PostgreSQL/Redis QA." 1; exit 1; }

ARGS=(run --rm qa_runner python scripts/run_e2e.py "${SCENARIOS[@]}" --browsers "$BROWSER" --output "$OUTPUT")
((FAIL_FAST)) && ARGS+=(--fail-fast)
set +e
"${COMPOSE[@]}" "${ARGS[@]}"
CODE=$?
set -e
[[ -f "$HOST_OUTPUT/summary.json" ]] || after_failure e2e-execution "El contenedor no genero summary.json." "$CODE"
echo "Resumen: $HOST_OUTPUT/summary.json"
exit "$CODE"
