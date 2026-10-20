# ES: Ejecuta el flujo operativo «install frontend dependencies» con fallos controlados y sin ocultar errores.
# EN: Runs the «install frontend dependencies» operational flow with controlled failures and visible errors.
[CmdletBinding()]
param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$Force
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$HtmxVersion = "2.0.10"
$ExpectedSha384 = "H5SrcfygHmAuTDZphMHqBJLc3FhssKjG7w/CeCpFReSfwBWDTKpkzPP8c+cLsK+V"
$HtmxUrls = @(
    "https://cdn.jsdelivr.net/npm/htmx.org@$HtmxVersion/dist/htmx.min.js",
    "https://unpkg.com/htmx.org@$HtmxVersion/dist/htmx.min.js"
)

# ES: La sección siguiente define precondiciones, límites y propagación explícita de fallos.
# EN: The following section defines preconditions, limits, and explicit failure propagation.
function Get-Sha384Base64 {
    param([Parameter(Mandatory = $true)][string]$Path)

    $Algorithm = [System.Security.Cryptography.SHA384]::Create()
    try {
        $Bytes = [System.IO.File]::ReadAllBytes($Path)
        return [Convert]::ToBase64String($Algorithm.ComputeHash($Bytes))
    }
    finally {
        $Algorithm.Dispose()
    }
}

$ResolvedProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
if (-not (Test-Path (Join-Path $ResolvedProjectRoot "manage.py") -PathType Leaf)) {
    throw "No se encontro manage.py en: $ResolvedProjectRoot"
}

$DestinationDirectory = Join-Path $ResolvedProjectRoot "static\vendor\htmx"
$Destination = Join-Path $DestinationDirectory "htmx.min.js"
New-Item -ItemType Directory -Path $DestinationDirectory -Force | Out-Null

if ((Test-Path $Destination -PathType Leaf) -and -not $Force) {
    $CurrentHash = Get-Sha384Base64 -Path $Destination
    if ($CurrentHash -eq $ExpectedSha384) {
        Write-Host "HTMX $HtmxVersion ya esta instalado y validado."
        return
    }
}

$TempFile = Join-Path ([System.IO.Path]::GetTempPath()) ("vinova-htmx-" + [Guid]::NewGuid().ToString("N") + ".js")
$Downloaded = $false
$LastError = $null

try {
    foreach ($Url in $HtmxUrls) {
        try {
            Write-Host "Descargando HTMX $HtmxVersion desde una distribucion oficial..."
            Invoke-WebRequest -Uri $Url -OutFile $TempFile -UseBasicParsing -TimeoutSec 60
            $ActualHash = Get-Sha384Base64 -Path $TempFile
            if ($ActualHash -ne $ExpectedSha384) {
                throw "La integridad SHA-384 de HTMX no coincide."
            }
            $Downloaded = $true
            break
        }
        catch {
            $LastError = $_
            Remove-Item $TempFile -Force -ErrorAction SilentlyContinue
        }
    }

    if (-not $Downloaded) {
        throw "No se pudo descargar y validar HTMX. Detalle: $($LastError.Exception.Message)"
    }

    Move-Item -Path $TempFile -Destination $Destination -Force
    Write-Host "HTMX $HtmxVersion instalado localmente en static/vendor/htmx/htmx.min.js."
}
finally {
    Remove-Item $TempFile -Force -ErrorAction SilentlyContinue
}
