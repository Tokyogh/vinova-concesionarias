# ES: Ejecuta el flujo operativo «validate nginx security» con fallos controlados y sin ocultar errores.
# EN: Runs the «validate nginx security» operational flow with controlled failures and visible errors.
[CmdletBinding()]
param(
    [string]$Image = "vinova-pro-nginx:2.0.0",
    [string]$TrivyImage = "aquasec/trivy:0.76.0@sha256:2416d1f74045b57274df1a340eee6b510cacd73c66a6ccb8da092b117eb7d222",
    [string]$OutputDir = "security-reports",
    [string]$CacheVolume = "vinova-trivy-cache"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
# ES: La sección siguiente define precondiciones, límites y propagación explícita de fallos.
# EN: The following section defines preconditions, limits, and explicit failure propagation.

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker no está instalado o no está disponible en PATH."
    exit 2
}

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ReportRoot = Join-Path $ProjectRoot $OutputDir
$NginxRoot = Join-Path $ProjectRoot "docker/nginx"
New-Item -ItemType Directory -Path $ReportRoot -Force | Out-Null

Write-Host "[1/5] Construyendo $Image sin caché..."
& docker build --no-cache -t $Image $NginxRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/5] Confirmando usuario no privilegiado..."
$Identity = (& docker run --rm --entrypoint id $Image | Out-String).Trim()
Write-Host $Identity
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($Identity -notmatch "uid=101\(nginx\)") {
    Write-Error "La imagen no se ejecuta con uid=101(nginx)."
    exit 1
}

Write-Host "[3/5] Generando reporte de configuración Trivy..."
& docker run --rm `
    -v "${NginxRoot}:/workspace:ro" `
    -v "${ReportRoot}:/reports" `
    -v "${CacheVolume}:/root/.cache/trivy" `
    $TrivyImage fs `
    --scanners misconfig `
    --severity HIGH,CRITICAL `
    --skip-version-check `
    --exit-code 0 `
    --format json `
    --output /reports/trivy-nginx-config.json `
    /workspace
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[4/5] Aplicando gate HIGH/CRITICAL a configuraciones..."
& docker run --rm `
    -v "${NginxRoot}:/workspace:ro" `
    -v "${CacheVolume}:/root/.cache/trivy" `
    $TrivyImage fs `
    --scanners misconfig `
    --severity HIGH,CRITICAL `
    --skip-version-check `
    --exit-code 1 `
    /workspace
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[5/5] Escaneando vulnerabilidades corregibles de la imagen..."
& docker run --rm `
    -v "/var/run/docker.sock:/var/run/docker.sock" `
    -v "${ReportRoot}:/reports" `
    -v "${CacheVolume}:/root/.cache/trivy" `
    $TrivyImage image `
    --scanners vuln `
    --severity HIGH,CRITICAL `
    --ignore-unfixed `
    --skip-version-check `
    --exit-code 0 `
    --format json `
    --output /reports/trivy-nginx-image.json `
    $Image
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& docker run --rm `
    -v "/var/run/docker.sock:/var/run/docker.sock" `
    -v "${CacheVolume}:/root/.cache/trivy" `
    $TrivyImage image `
    --scanners vuln `
    --severity HIGH,CRITICAL `
    --ignore-unfixed `
    --skip-version-check `
    --exit-code 1 `
    $Image
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Validación NGINX aprobada: uid=101 y sin HIGH/CRITICAL corregibles según Trivy."
Write-Host "Reportes JSON: $ReportRoot"
