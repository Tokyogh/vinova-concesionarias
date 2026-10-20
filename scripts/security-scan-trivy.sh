#!/usr/bin/env bash
# ES: Ejecuta el flujo operativo «security scan trivy» con fallos controlados y sin ocultar errores.
# EN: Runs the «security scan trivy» operational flow with controlled failures and visible errors.
set -Eeuo pipefail

usage() {
    cat <<'EOF'
Uso:
  ./scripts/security-scan-trivy.sh filesystem [opciones]
  ./scripts/security-scan-trivy.sh image --image NOMBRE [opciones]
  ./scripts/security-scan-trivy.sh all --image NOMBRE [opciones]

Opciones:
  --strict            Devuelve código 1 si hay hallazgos HIGH/CRITICAL.
  --include-unfixed   Incluye vulnerabilidades todavía sin corrección.
  --include-secrets   Activa también el escáner de secretos.
  --output-dir RUTA   Carpeta de reportes. Predeterminado: security-reports.
EOF
}

TARGET="${1:-filesystem}"
if [[ $# -gt 0 ]]; then
    shift
fi

IMAGE="vinova-pro-nginx:1.0.1"
STRICT="false"
INCLUDE_UNFIXED="false"
INCLUDE_SECRETS="false"
OUTPUT_DIR="security-reports"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --image)
            IMAGE="${2:-}"
            shift 2
            ;;
        --strict)
            STRICT="true"
            shift
            ;;
        --include-unfixed)
            INCLUDE_UNFIXED="true"
            shift
            ;;
        --include-secrets)
            INCLUDE_SECRETS="true"
            shift
            ;;
        --output-dir)
            OUTPUT_DIR="${2:-}"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Opción desconocida: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ "$TARGET" != "filesystem" && "$TARGET" != "image" && "$TARGET" != "all" ]]; then
    echo "Target inválido: $TARGET" >&2
    usage >&2
    exit 2
fi

if ! command -v trivy >/dev/null 2>&1; then
    echo "Trivy no está instalado o no está disponible en PATH." >&2
    exit 2
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_ROOT="$PROJECT_ROOT/$OUTPUT_DIR"
CACHE_ROOT="$PROJECT_ROOT/.trivy-cache"
mkdir -p "$REPORT_ROOT" "$CACHE_ROOT"

COMMON_ARGS=(
    --severity HIGH,CRITICAL
    --timeout 10m
    --cache-dir "$CACHE_ROOT"
    --disable-telemetry
)

if [[ "$INCLUDE_UNFIXED" != "true" ]]; then
    COMMON_ARGS+=(--ignore-unfixed)
fi

POLICY_EXIT_CODE=0
if [[ "$STRICT" == "true" ]]; then
    POLICY_EXIT_CODE=1
fi

RESULT_EXIT_CODE=0

# ES: La sección siguiente define precondiciones, límites y propagación explícita de fallos.
# EN: The following section defines preconditions, limits, and explicit failure propagation.
run_scan() {
    local subcommand="$1"
    local subject="$2"
    local report_name="$3"
    local scanners="$4"
    local json_report="$REPORT_ROOT/$report_name.json"

    echo "Generando reporte JSON: $json_report"
    trivy "$subcommand" "${COMMON_ARGS[@]}" \
        --scanners "$scanners" \
        --exit-code 0 \
        --format json \
        --output "$json_report" \
        "$subject"

    echo "Mostrando resultados HIGH/CRITICAL para: $subject"
    set +e
    trivy "$subcommand" "${COMMON_ARGS[@]}" \
        --scanners "$scanners" \
        --exit-code "$POLICY_EXIT_CODE" \
        --format table \
        "$subject"
    local code=$?
    set -e

    if [[ $code -ne 0 ]]; then
        RESULT_EXIT_CODE=$code
    fi
}

FILESYSTEM_SCANNERS="vuln,misconfig"
IMAGE_SCANNERS="vuln"
if [[ "$INCLUDE_SECRETS" == "true" ]]; then
    FILESYSTEM_SCANNERS="vuln,misconfig,secret"
    IMAGE_SCANNERS="vuln,secret"
fi

if [[ "$TARGET" == "filesystem" || "$TARGET" == "all" ]]; then
    run_scan \
        fs \
        "$PROJECT_ROOT" \
        trivy-filesystem \
        "$FILESYSTEM_SCANNERS"
fi

if [[ "$TARGET" == "image" || "$TARGET" == "all" ]]; then
    SAFE_IMAGE_NAME="$(printf '%s' "$IMAGE" | sed 's/[^A-Za-z0-9_.-]/-/g')"
    run_scan \
        image \
        "$IMAGE" \
        "trivy-image-$SAFE_IMAGE_NAME" \
        "$IMAGE_SCANNERS"
fi

if [[ $RESULT_EXIT_CODE -eq 0 ]]; then
    echo "Escaneo Trivy completado. Reportes: $REPORT_ROOT"
elif [[ "$STRICT" == "true" ]]; then
    echo "Trivy encontró hallazgos que bloquean el modo estricto." >&2
fi

exit "$RESULT_EXIT_CODE"
