# ES: Ejecuta el flujo operativo «validate staging» con fallos controlados y sin ocultar errores.
# EN: Runs the «validate staging» operational flow with controlled failures and visible errors.
param(
    [string]$BaseUrl = "",
    [string]$EnvFile = ".env.staging",
    [int]$TimeoutSeconds = 180,
    [switch]$RunSmoke
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# ES: La sección siguiente define precondiciones, límites y propagación explícita de fallos.
# EN: The following section defines preconditions, limits, and explicit failure propagation.
function Read-EnvValue([string]$Key) {
    $line = Get-Content -LiteralPath $EnvFile | Where-Object {
        $_ -match "^\s*$([regex]::Escape($Key))="
    } | Select-Object -Last 1
    if (-not $line) { return "" }
    return ($line -split "=", 2)[1].Trim()
}

if (-not $BaseUrl) {
    $BaseUrl = Read-EnvValue "VINOVA_SMOKE_BASE_URL"
}
if (-not $BaseUrl) { throw "Falta BaseUrl y VINOVA_SMOKE_BASE_URL no esta configurado." }

& "$PSScriptRoot/staging-preflight.ps1" -EnvFile $EnvFile

$ComposeArgs = @(
    "--env-file", $EnvFile,
    "-f", "docker-compose.prod.yml",
    "-f", "docker-compose.staging.yml"
)

$appInitId = (& docker compose @ComposeArgs ps -a -q app_init).Trim()
if (-not $appInitId) { throw "No existe el contenedor app_init. Ejecute deploy-staging.ps1 primero." }
$appInitExit = (& docker inspect --format "{{.State.ExitCode}}" $appInitId).Trim()
if ($appInitExit -ne "0") {
    & docker compose @ComposeArgs logs --no-color --tail=200 app_init
    throw "app_init termino con codigo $appInitExit."
}

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$requiredServices = @("db", "redis", "web", "celery_worker", "celery_beat", "nginx")
do {
    $pending = @()
    foreach ($service in $requiredServices) {
        $containerId = (& docker compose @ComposeArgs ps -q $service).Trim()
        if (-not $containerId) {
            $pending += "${service}:no-creado"
            continue
        }
        $state = (& docker inspect --format "{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}" $containerId).Trim()
        $parts = $state -split "\|", 2
        $status = $parts[0]
        $health = $parts[1]
        if ($status -ne "running" -or ($health -ne "none" -and $health -ne "healthy")) {
            $pending += "${service}:$state"
        }
    }
    if ($pending.Count -eq 0) { break }
    Start-Sleep -Seconds 3
} while ((Get-Date) -lt $deadline)

if ($pending.Count -gt 0) {
    & docker compose @ComposeArgs ps -a
    & docker compose @ComposeArgs logs --no-color --tail=150 web nginx celery_worker celery_beat
    throw "Servicios no saludables: $($pending -join ', ')."
}

$uri = [Uri]$BaseUrl
$curlArgs = @("--fail", "--silent", "--show-error", "--location")
if ($uri.Scheme -eq "https" -and $uri.Host -in @("localhost", "127.0.0.1", "::1")) {
    $curlArgs += "--insecure"
}
foreach ($path in @("/nginx-health", "/health/live/", "/health/ready/")) {
    & curl.exe @curlArgs "$($BaseUrl.TrimEnd('/'))$path" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Fallo la validacion HTTP de $path." }
}

& docker compose @ComposeArgs ps -a
Write-Host "Staging saludable: app_init=0, contenedores healthy y endpoints operativos."

if ($RunSmoke) {
    & "$PSScriptRoot/smoke-staging-read.ps1" -BaseUrl $BaseUrl -EnvFile $EnvFile
    if ($LASTEXITCODE -ne 0) { throw "El smoke de lectura fallo." }
}
