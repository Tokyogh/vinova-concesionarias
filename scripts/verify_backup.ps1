# ES: Ejecuta el flujo operativo «verify backup» con fallos controlados y sin ocultar errores.
# EN: Runs the «verify backup» operational flow with controlled failures and visible errors.
param([Parameter(Mandatory=$true)][string]$BackupId)
$ErrorActionPreference = "Stop"
docker compose run --rm web python manage.py verify_vinova_backup $BackupId
if ($LASTEXITCODE -ne 0) { throw "La verificación falló." }
