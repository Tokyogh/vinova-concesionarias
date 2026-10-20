#!/usr/bin/env bash
# ES: Ejecuta el flujo operativo «restore db» con fallos controlados y sin ocultar errores.
# EN: Runs the «restore db» operational flow with controlled failures and visible errors.
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Uso: ./scripts/restore_db.sh backups/archivo.dump [RESTORE]"
  exit 1
fi
if [ "${2:-}" != "RESTORE" ]; then
  echo "Operación cancelada. Para restaurar, agrega la confirmación RESTORE."
  echo "Ejemplo: ./scripts/restore_db.sh $1 RESTORE"
  exit 1
fi

FILE="$1"
if [ ! -f "$FILE" ]; then
  echo "No existe el archivo: $FILE"
  exit 1
fi
if [ -f "${FILE}.sha256" ]; then
  sha256sum -c "${FILE}.sha256"
fi

cat <<'NOTICE'
ADVERTENCIA: esta operación modifica la base configurada.
Debe ejecutarse primero en un entorno aislado y con un backup reciente verificado.
NOTICE

docker compose exec -T db pg_restore -U "${POSTGRES_USER:-vinova}" -d "${POSTGRES_DB:-vinova_pro}" --clean --if-exists --no-owner --no-acl < "$FILE"
echo "Restauración PostgreSQL finalizada. Ejecuta migrate, check y pruebas funcionales."
