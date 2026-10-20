# ES: Ejecuta el flujo operativo «smoke staging write» con fallos controlados y sin ocultar errores.
# EN: Runs the «smoke staging write» operational flow with controlled failures and visible errors.
param([Parameter(Mandatory=$true)][string]$BaseUrl, [Parameter(Mandatory=$true)][string]$Confirm)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if ($Confirm -ne "CONFIRM_WRITE") { throw "Se requiere CONFIRM_WRITE." }
if ($env:VINOVA_SMOKE_ALLOW_WRITE -ne "true") { throw "Defina VINOVA_SMOKE_ALLOW_WRITE=true." }
if (-not $env:VINOVA_SMOKE_USERNAME -or -not $env:VINOVA_SMOKE_PASSWORD) { throw "Faltan credenciales smoke." }

$Uri = [System.Uri]$BaseUrl
$TlsArguments = @()
if ($Uri.Scheme -eq "https" -and $Uri.Host -in @("localhost", "127.0.0.1", "::1")) {
    $TlsArguments += "--insecure-local-tls"
}

& "$PSScriptRoot/qa-deployment-smoke.ps1" $BaseUrl --mode staging @TlsArguments --write-tests --cleanup `
  --scenario public --scenario auth --scenario health --scenario navigation --scenario security `
  --scenario customers --scenario vehicles --scenario inventory --scenario sales `
  --scenario documents --scenario accessibility --scenario cleanup `
  --timeout $(if ($env:VINOVA_SMOKE_TIMEOUT) {$env:VINOVA_SMOKE_TIMEOUT} else {30}) `
  --retries $(if ($env:VINOVA_SMOKE_RETRIES) {$env:VINOVA_SMOKE_RETRIES} else {0})
if ($LASTEXITCODE -ne 0) { throw "El smoke de escritura fallo." }
