# ES: Ejecuta el flujo operativo «backup all» con fallos controlados y sin ocultar errores.
# EN: Runs the «backup all» operational flow with controlled failures and visible errors.
$ErrorActionPreference = "Stop"
Write-Host "Creando backup completo verificable de Vinova Pro..."
docker compose run --rm web python manage.py create_vinova_backup --type full
if ($LASTEXITCODE -ne 0) { throw "El backup no pudo completarse." }
Write-Host "Consulta el historial en http://localhost:8000/dashboard/continuity/"
