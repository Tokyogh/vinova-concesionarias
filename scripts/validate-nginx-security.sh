#!/usr/bin/env bash
# ES: Ejecuta el flujo operativo «validate nginx security» con fallos controlados y sin ocultar errores.
# EN: Runs the «validate nginx security» operational flow with controlled failures and visible errors.
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NGINX_ROOT="$PROJECT_ROOT/docker/nginx"
IMAGE="${VINOVA_NGINX_IMAGE:-vinova-pro-nginx:1.0.1}"
TRIVY_IMAGE="${TRIVY_IMAGE:-aquasec/trivy:0.76.0@sha256:2416d1f74045b57274df1a340eee6b510cacd73c66a6ccb8da092b117eb7d222}"
REPORT_ROOT="${VINOVA_SECURITY_REPORT_DIR:-$PROJECT_ROOT/security-reports}"
CACHE_VOLUME="${VINOVA_TRIVY_CACHE_VOLUME:-vinova-trivy-cache}"

# ES: La sección siguiente define precondiciones, límites y propagación explícita de fallos.
# EN: The following section defines preconditions, limits, and explicit failure propagation.
command -v docker >/dev/null 2>&1 || {
    echo "Docker no está instalado o no está disponible en PATH." >&2
    exit 2
}

mkdir -p "$REPORT_ROOT"

echo "[1/5] Construyendo $IMAGE sin caché..."
docker build --no-cache -t "$IMAGE" "$NGINX_ROOT"

echo "[2/5] Confirmando usuario no privilegiado..."
IDENTITY="$(docker run --rm --entrypoint id "$IMAGE")"
printf '%s\n' "$IDENTITY"
case "$IDENTITY" in
    *"uid=101(nginx)"*) ;;
    *)
        echo "La imagen no se ejecuta con uid=101(nginx)." >&2
        exit 1
        ;;
esac

echo "[3/5] Generando reporte de configuración Trivy..."
docker run --rm \
    -v "$NGINX_ROOT:/workspace:ro" \
    -v "$REPORT_ROOT:/reports" \
    -v "$CACHE_VOLUME:/root/.cache/trivy" \
    "$TRIVY_IMAGE" fs \
    --scanners misconfig \
    --severity HIGH,CRITICAL \
    --skip-version-check \
    --exit-code 0 \
    --format json \
    --output /reports/trivy-nginx-config.json \
    /workspace

echo "[4/5] Aplicando gate HIGH/CRITICAL a configuraciones..."
docker run --rm \
    -v "$NGINX_ROOT:/workspace:ro" \
    -v "$CACHE_VOLUME:/root/.cache/trivy" \
    "$TRIVY_IMAGE" fs \
    --scanners misconfig \
    --severity HIGH,CRITICAL \
    --skip-version-check \
    --exit-code 1 \
    /workspace

echo "[5/5] Escaneando vulnerabilidades corregibles de la imagen..."
docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$REPORT_ROOT:/reports" \
    -v "$CACHE_VOLUME:/root/.cache/trivy" \
    "$TRIVY_IMAGE" image \
    --scanners vuln \
    --severity HIGH,CRITICAL \
    --ignore-unfixed \
    --skip-version-check \
    --exit-code 0 \
    --format json \
    --output /reports/trivy-nginx-image.json \
    "$IMAGE"

docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$CACHE_VOLUME:/root/.cache/trivy" \
    "$TRIVY_IMAGE" image \
    --scanners vuln \
    --severity HIGH,CRITICAL \
    --ignore-unfixed \
    --skip-version-check \
    --exit-code 1 \
    "$IMAGE"

echo "Validación NGINX aprobada: uid=101 y sin HIGH/CRITICAL corregibles según Trivy."
echo "Reportes JSON: $REPORT_ROOT"
