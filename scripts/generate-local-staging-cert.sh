#!/usr/bin/env bash
# ES: Ejecuta el flujo operativo «generate local staging cert» con fallos controlados y sin ocultar errores.
# EN: Runs the «generate local staging cert» operational flow with controlled failures and visible errors.
set -euo pipefail
HOST="${1:-localhost}"
OUT_DIR="${2:-docker/nginx/certs}"
DAYS="${3:-30}"
command -v openssl >/dev/null 2>&1 || { echo "OpenSSL es obligatorio." >&2; exit 1; }
[[ "$DAYS" =~ ^[0-9]+$ ]] && (( DAYS >= 1 && DAYS <= 825 )) || { echo "DAYS debe estar entre 1 y 825." >&2; exit 1; }
mkdir -p "$OUT_DIR"
openssl req -x509 -nodes -newkey rsa:3072 -days "$DAYS" \
  -keyout "$OUT_DIR/privkey.pem" -out "$OUT_DIR/fullchain.pem" \
  -subj "/CN=$HOST" -addext "subjectAltName=DNS:$HOST,DNS:localhost,IP:127.0.0.1"
chmod 644 "$OUT_DIR/fullchain.pem" "$OUT_DIR/privkey.pem"
echo "Certificado temporal local creado para $HOST por $DAYS dias. Reemplacelo en staging empresarial."
