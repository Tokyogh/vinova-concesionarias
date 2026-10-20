# ES: Ejecuta el flujo operativo «security scan trivy» con fallos controlados y sin ocultar errores.
# EN: Runs the «security scan trivy» operational flow with controlled failures and visible errors.
[CmdletBinding()]
param(
    [ValidateSet("filesystem", "image", "all")]
    [string]$Target = "filesystem",

    [string]$Image = "vinova-pro-nginx:2.0.0",

    [switch]$Strict,

    [switch]$IncludeUnfixed,

    [switch]$IncludeSecrets,

    [string]$OutputDir = "security-reports"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Get-Command trivy -ErrorAction SilentlyContinue)) {
    Write-Error "Trivy no está instalado o no está disponible en PATH."
    exit 2
}

$ReportRoot = Join-Path $ProjectRoot $OutputDir
$CacheRoot = Join-Path $ProjectRoot ".trivy-cache"
New-Item -ItemType Directory -Path $ReportRoot -Force | Out-Null
New-Item -ItemType Directory -Path $CacheRoot -Force | Out-Null

$CommonArguments = @(
    "--severity", "HIGH,CRITICAL",
    "--timeout", "10m",
    "--cache-dir", $CacheRoot,
    "--disable-telemetry"
)

if (-not $IncludeUnfixed) {
    $CommonArguments += "--ignore-unfixed"
}

$ResultExitCode = 0
$PolicyExitCode = if ($Strict) { "1" } else { "0" }

# ES: La sección siguiente define precondiciones, límites y propagación explícita de fallos.
# EN: The following section defines preconditions, limits, and explicit failure propagation.
function Invoke-TrivyTarget {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Subcommand,

        [Parameter(Mandatory = $true)]
        [string]$Subject,

        [Parameter(Mandatory = $true)]
        [string]$ReportName,

        [Parameter(Mandatory = $true)]
        [string]$Scanners
    )

    $JsonReport = Join-Path $ReportRoot "$ReportName.json"

    Write-Host "Generando reporte JSON: $JsonReport"
    & trivy $Subcommand @CommonArguments `
        --scanners $Scanners `
        --exit-code 0 `
        --format json `
        --output $JsonReport `
        $Subject

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Trivy no pudo generar el reporte para $Subject."
        return $LASTEXITCODE
    }

    Write-Host "Mostrando resultados HIGH/CRITICAL para: $Subject"
    & trivy $Subcommand @CommonArguments `
        --scanners $Scanners `
        --exit-code $PolicyExitCode `
        --format table `
        $Subject

    return $LASTEXITCODE
}

$FilesystemScanners = if ($IncludeSecrets) {
    "vuln,misconfig,secret"
} else {
    "vuln,misconfig"
}

$ImageScanners = if ($IncludeSecrets) {
    "vuln,secret"
} else {
    "vuln"
}

if ($Target -eq "filesystem" -or $Target -eq "all") {
    $Code = Invoke-TrivyTarget `
        -Subcommand "fs" `
        -Subject $ProjectRoot `
        -ReportName "trivy-filesystem" `
        -Scanners $FilesystemScanners

    if ($Code -ne 0) {
        $ResultExitCode = $Code
    }
}

if ($Target -eq "image" -or $Target -eq "all") {
    $SafeImageName = $Image -replace "[^A-Za-z0-9_.-]", "-"
    $Code = Invoke-TrivyTarget `
        -Subcommand "image" `
        -Subject $Image `
        -ReportName "trivy-image-$SafeImageName" `
        -Scanners $ImageScanners

    if ($Code -ne 0) {
        $ResultExitCode = $Code
    }
}

if ($ResultExitCode -eq 0) {
    Write-Host "Escaneo Trivy completado. Reportes: $ReportRoot"
} elseif ($Strict) {
    Write-Error "Trivy encontró hallazgos que bloquean el modo estricto."
}

exit $ResultExitCode
