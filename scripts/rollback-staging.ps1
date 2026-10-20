# ES: Ejecuta el flujo operativo «rollback staging» con fallos controlados y sin ocultar errores.
# EN: Runs the «rollback staging» operational flow with controlled failures and visible errors.
param(
  [Parameter(Mandatory=$true)][string]$PreviousRelease,
  [string]$EnvFile = ".env.staging",
  [Parameter(Mandatory=$true)][string]$Confirm
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if ($Confirm -ne "ROLLBACK_STAGING") { throw "Confirmación exacta requerida: ROLLBACK_STAGING" }
if (-not (Test-Path -LiteralPath $PreviousRelease -PathType Container)) { throw "No existe el release anterior." }
if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) { throw "No existe $EnvFile." }
$EnvFile = (Resolve-Path -LiteralPath $EnvFile).Path
Set-Location $PreviousRelease
$composeArgs = @("--env-file", $EnvFile, "-f", "docker-compose.prod.yml")
if (Test-Path -LiteralPath "docker-compose.staging.yml") { $composeArgs += @("-f", "docker-compose.staging.yml") }
& docker compose @composeArgs config --quiet
if ($LASTEXITCODE -ne 0) { throw "El release anterior no tiene Compose válido." }
& docker compose @composeArgs up -d --build
if ($LASTEXITCODE -ne 0) { throw "Falló el rollback." }
Write-Host "Rollback no destructivo iniciado. No se eliminaron volúmenes. Ejecute el smoke de lectura."
