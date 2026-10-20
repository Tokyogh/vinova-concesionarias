# ES: Ejecuta el flujo operativo «staging preflight» con fallos controlados y sin ocultar errores.
# EN: Runs the «staging preflight» operational flow with controlled failures and visible errors.
param([string]$EnvFile = ".env.staging", [string]$BaseUrl = "")
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) { throw "No existe $EnvFile." }
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "Python no esta disponible." }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "Docker no esta disponible." }

& python "$PSScriptRoot/check_staging_env.py" --env-file $EnvFile
if ($LASTEXITCODE -ne 0) { throw "El archivo de entorno de staging no es consistente." }

& python "$PSScriptRoot/check_frontend_dependencies.py"
if ($LASTEXITCODE -ne 0) { throw "Las dependencias frontend locales no son validas." }

& docker compose version | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Docker Compose v2 no esta disponible." }

$ComposeArgs = @(
    "--env-file", $EnvFile,
    "-f", "docker-compose.prod.yml",
    "-f", "docker-compose.staging.yml"
)
& docker compose @ComposeArgs config --quiet
if ($LASTEXITCODE -ne 0) { throw "La configuracion Compose no es valida." }

if ($BaseUrl) {
    $uri = [Uri]$BaseUrl
    if ($uri.Scheme -ne "https") { throw "BaseUrl debe usar HTTPS." }
    [void][System.Net.Dns]::GetHostAddresses($uri.Host)
}

Write-Host "Preflight de staging aprobado para $EnvFile."
