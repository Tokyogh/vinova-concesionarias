# ES: Ejecuta el flujo operativo «deploy staging» con fallos controlados y sin ocultar errores.
# EN: Runs the «deploy staging» operational flow with controlled failures and visible errors.
param(
    [string]$EnvFile = ".env.staging",
    [switch]$SkipBuild
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$ComposeArgs = @(
    "--env-file", $EnvFile,
    "-f", "docker-compose.prod.yml",
    "-f", "docker-compose.staging.yml"
)

& "$PSScriptRoot/staging-preflight.ps1" -EnvFile $EnvFile

if (-not $SkipBuild) {
    & docker compose @ComposeArgs build --pull
    if ($LASTEXITCODE -ne 0) { throw "Fallo el build de staging." }
}

& docker compose @ComposeArgs up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "Estado de los servicios:" -ForegroundColor Yellow
    & docker compose @ComposeArgs ps -a
    Write-Host "Logs de dependencias y app_init:" -ForegroundColor Yellow
    & docker compose @ComposeArgs logs --no-color --tail=200 db redis app_init
    throw "Fallo el arranque de staging. La causa aparece en los logs anteriores."
}

& docker compose @ComposeArgs ps -a
Write-Host "Staging iniciado. Continue con validate-staging.ps1."
