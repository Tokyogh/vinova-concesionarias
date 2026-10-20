# ES: Ejecuta el flujo operativo «smoke staging read» con fallos controlados y sin ocultar errores.
# EN: Runs the «smoke staging read» operational flow with controlled failures and visible errors.
[CmdletBinding()]
param(
    [string]$BaseUrl = "",
    [string]$EnvFile = ".env.staging"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EnvPath = if ([System.IO.Path]::IsPathRooted($EnvFile)) {
    $EnvFile
} else {
    Join-Path $ProjectRoot $EnvFile
}

# ES: La sección siguiente define precondiciones, límites y propagación explícita de fallos.
# EN: The following section defines preconditions, limits, and explicit failure propagation.
function Read-EnvValue {
    param([Parameter(Mandatory = $true)][string]$Key)

    if (-not (Test-Path -LiteralPath $EnvPath -PathType Leaf)) {
        return ""
    }
    $Line = Get-Content -LiteralPath $EnvPath | Where-Object {
        $_ -match "^\s*$([regex]::Escape($Key))="
    } | Select-Object -Last 1
    if (-not $Line) {
        return ""
    }
    return ($Line -split "=", 2)[1].Trim()
}

# Las variables ya exportadas en la sesion tienen prioridad. El archivo permite
# una ejecucion repetible sin obligar a copiar manualmente timeout, URL o las
# credenciales tecnicas en cada consola.
foreach ($Key in @(
    "VINOVA_SMOKE_USERNAME",
    "VINOVA_SMOKE_PASSWORD",
    "VINOVA_SMOKE_TIMEOUT",
    "VINOVA_SMOKE_RETRIES",
    "VINOVA_SMOKE_REPORT_DIR"
)) {
    if (-not [Environment]::GetEnvironmentVariable($Key, "Process")) {
        $Value = Read-EnvValue -Key $Key
        if ($Value) {
            [Environment]::SetEnvironmentVariable($Key, $Value, "Process")
        }
    }
}

if (-not $BaseUrl) {
    $BaseUrl = Read-EnvValue -Key "VINOVA_SMOKE_BASE_URL"
}
if (-not $BaseUrl) {
    $BaseUrl = "https://localhost"
}

$Uri = [System.Uri]$BaseUrl
$Arguments = @(
    $BaseUrl,
    "--mode", "staging",
    "--scenario", "tls",
    "--scenario", "public",
    "--scenario", "auth",
    "--scenario", "health",
    "--scenario", "assets",
    "--scenario", "navigation",
    "--scenario", "security",
    "--scenario", "accessibility",
    "--timeout", $(if ($env:VINOVA_SMOKE_TIMEOUT) { $env:VINOVA_SMOKE_TIMEOUT } else { "30" }),
    "--retries", $(if ($env:VINOVA_SMOKE_RETRIES) { $env:VINOVA_SMOKE_RETRIES } else { "1" })
)

if ($Uri.Scheme -eq "https" -and $Uri.Host -in @("localhost", "127.0.0.1", "::1")) {
    $Arguments += "--insecure-local-tls"
}

& "$PSScriptRoot/qa-deployment-smoke.ps1" @Arguments
if ($LASTEXITCODE -ne 0) {
    throw "El smoke de lectura fallo."
}
