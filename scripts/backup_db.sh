#!/usr/bin/env bash
# ES: Ejecuta el flujo operativo «backup db» con fallos controlados y sin ocultar errores.
# EN: Runs the «backup db» operational flow with controlled failures and visible errors.
set -euo pipefail

# Backup PostgreSQL manual desde el contenedor de base de datos.
# Para el paquete completo (DB + media + private + manifiesto) use:
# docker compose run --rm web python manage.py create_vinova_backup --type full

mkdir -p backups
STAMP=$(date +%Y%m%d_%H%M%S)
FILE="backups/vinova_pro_${STAMP}.dump"
docker compose exec -T db pg_dump -U "${POSTGRES_USER:-vinova}" -d "${POSTGRES_DB:-vinova_pro}" --format=custom --no-owner --no-acl > "$FILE"
sha256sum "$FILE" > "${FILE}.sha256"
echo "Backup PostgreSQL creado: $FILE"
echo "Checksum: ${FILE}.sha256"
