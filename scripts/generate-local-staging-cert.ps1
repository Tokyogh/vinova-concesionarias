# ES: Ejecuta el flujo operativo «generate local staging cert» con fallos controlados y sin ocultar errores.
# EN: Runs the «generate local staging cert» operational flow with controlled failures and visible errors.
param(
    [string]$HostName = "localhost",
    [string]$OutputDir = "docker/nginx/certs",
    [int]$Days = 30
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if (-not (Get-Command openssl -ErrorAction SilentlyContinue)) { throw "OpenSSL es obligatorio." }
if ($Days -lt 1 -or $Days -gt 825) { throw "Days debe estar entre 1 y 825." }
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
& openssl req -x509 -nodes -newkey rsa:3072 -days $Days `
  -keyout "$OutputDir/privkey.pem" -out "$OutputDir/fullchain.pem" `
  -subj "/CN=$HostName" -addext "subjectAltName=DNS:$HostName,DNS:localhost,IP:127.0.0.1"
if ($LASTEXITCODE -ne 0) { throw "No se pudo generar el certificado." }
Write-Host "Certificado temporal local creado para $HostName por $Days dias. Reemplacelo en staging empresarial."
