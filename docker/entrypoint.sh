#!/bin/sh
# ES: Ejecuta el flujo operativo «entrypoint» con fallos controlados y sin ocultar errores.
# EN: Runs the «entrypoint» operational flow with controlled failures and visible errors.
# Initializes writable directories and starts the selected application process.
set -eu

# Los archivos privados conservan una umask restrictiva. Los directorios
# servidos por Nginx usan un grupo compartido y setgid para que UID 101 pueda
# leer CSS, JavaScript e imágenes sin permisos globales.
umask 027
SHARED_GID="${VINOVA_SHARED_ASSETS_GID:-101}"

mkdir -p /app/staticfiles /app/media /app/private /app/logs /app/run

for directory in /app/staticfiles /app/media; do
  # Best-effort: en bind mounts (Docker Desktop/WSL2) el usuario no root
  # puede carecer de permiso para cambiar el grupo. En producción, donde el
  # volumen es propiedad del usuario, la operación se aplica normalmente.
  chgrp "$SHARED_GID" "$directory" 2>/dev/null || true
  chmod 2750 "$directory" 2>/dev/null || true
done

exec "$@"
