#!/usr/bin/env bash
# ES: Ejecuta el flujo operativo «vinova qa» con fallos controlados y sin ocultar errores.
# EN: Runs the «vinova qa» operational flow with controlled failures and visible errors.
set -Eeuo pipefail

PROFILE="${1:-quick}"
case "$PROFILE" in
  quick|full|release) ;;
  *) echo "Uso: ./scripts/vinova-qa.sh [quick|full|release]" >&2; exit 2 ;;
esac

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_NAME="${VINOVA_QA_PROJECT_NAME:-vinova-qa-cli}"
COMPOSE=(docker compose --project-name "$PROJECT_NAME" -f "$PROJECT_ROOT/docker-compose.qa-cli.yml")

mkdir -p "$PROJECT_ROOT/private/qa_reports"
cd "$PROJECT_ROOT"
cleanup() { "${COMPOSE[@]}" down --remove-orphans >/dev/null 2>&1 || true; }
trap cleanup EXIT

docker info >/dev/null 2>&1 || { echo "Docker no esta iniciado o el motor no responde." >&2; exit 1; }
"${COMPOSE[@]}" config --quiet

IMAGE_ID="$("${COMPOSE[@]}" images -q qa_runner 2>/dev/null | head -n1 || true)"
if [[ -z "$IMAGE_ID" ]]; then
  echo "La imagen QA no existe; construyendo una sola vez..."
  "${COMPOSE[@]}" build qa_runner
else
  echo "Reutilizando la imagen QA existente; el codigo actual se monta en modo solo lectura."
fi

echo "Iniciando PostgreSQL y Redis temporales..."
if ! "${COMPOSE[@]}" up -d --wait qa_db qa_redis; then
  "${COMPOSE[@]}" ps --all || true
  "${COMPOSE[@]}" logs --tail=120 qa_db qa_redis || true
  echo "No se pudo iniciar la infraestructura QA. Revisa el diagnostico anterior." >&2
  exit 1
fi

export VINOVA_QA_PROFILE="$PROFILE"
"${COMPOSE[@]}" run --rm -e VINOVA_QA_PROFILE="$PROFILE" qa_runner \
  python scripts/vinova_qa.py --profile "$PROFILE"
