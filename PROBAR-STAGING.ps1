# ES: Ejecuta el flujo operativo «PROBAR STAGING» con fallos controlados y sin ocultar errores.
# EN: Runs the «PROBAR STAGING» operational flow with controlled failures and visible errors.
[CmdletBinding()]
param(
    [Parameter(Position = 0)][string]$ProjectRoot = "",
    [string]$EnvFile = ".env.staging",
    [string]$BaseUrl = "",
    [switch]$SkipBuild,
    [switch]$ReadOnly
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not $ProjectRoot) { $ProjectRoot = (Get-Location).Path }
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
if (-not (Test-Path (Join-Path $ProjectRoot "manage.py") -PathType Leaf)) {
    throw "Indique la raiz de Vinova Pro: PROBAR-STAGING.bat C:\ruta\vinova-cns+"
}

$EnvPath = if ([System.IO.Path]::IsPathRooted($EnvFile)) { $EnvFile } else { Join-Path $ProjectRoot $EnvFile }
if (-not (Test-Path $EnvPath -PathType Leaf)) { throw "No existe $EnvPath" }

# ES: La sección siguiente define precondiciones, límites y propagación explícita de fallos.
# EN: The following section defines preconditions, limits, and explicit failure propagation.
function Read-EnvValue([string]$Key) {
    $Line = Get-Content -LiteralPath $EnvPath | Where-Object {
        $_ -match "^\s*$([regex]::Escape($Key))="
    } | Select-Object -Last 1
    if (-not $Line) { return "" }
    return ($Line -split "=", 2)[1].Trim()
}

function Assert-LastExitCode([string]$Message) {
    if ($LASTEXITCODE -ne 0) { throw $Message }
}

if (-not $BaseUrl) { $BaseUrl = Read-EnvValue "VINOVA_SMOKE_BASE_URL" }
if (-not $BaseUrl) { $BaseUrl = "https://localhost" }

$ComposeArgs = @(
    "--env-file", $EnvFile,
    "-f", "docker-compose.prod.yml",
    "-f", "docker-compose.staging.yml"
)

$RevisionFile = Join-Path $ProjectRoot "scripts\staging-bot-revision.txt"
$LocalRevision = if (Test-Path $RevisionFile -PathType Leaf) {
    (Get-Content -LiteralPath $RevisionFile -Raw).Trim()
}
else {
    ""
}
$EffectiveSkipBuild = [bool]$SkipBuild
if ($SkipBuild -and $LocalRevision) {
    $ContainerRevisionLines = @(& docker compose @ComposeArgs exec -T web sh -lc "cat /app/scripts/staging-bot-revision.txt 2>/dev/null || true" 2>$null)
    $ContainerRevision = ($ContainerRevisionLines | ForEach-Object { [string]$_ }) -join "`n"
    $ContainerRevision = $ContainerRevision.Trim()
    if ($ContainerRevision -ne $LocalRevision) {
        Write-Host "El codigo local del bot cambio ($ContainerRevision -> $LocalRevision). Se reconstruiran las imagenes una sola vez." -ForegroundColor Yellow
        $EffectiveSkipBuild = $false
    }
}
$RunId = ([guid]::NewGuid().ToString("N")).Substring(0, 12)
$ContainerManifest = "/app/run/vinova-smoke-roles-$RunId.json"
$LocalManifest = Join-Path ([System.IO.Path]::GetTempPath()) "vinova-smoke-roles-$RunId.json"
$Provisioned = $false
$PreviousSmokeUser = [Environment]::GetEnvironmentVariable("VINOVA_SMOKE_USERNAME", "Process")
$PreviousSmokePassword = [Environment]::GetEnvironmentVariable("VINOVA_SMOKE_PASSWORD", "Process")
$PreviousAllowWrite = [Environment]::GetEnvironmentVariable("VINOVA_SMOKE_ALLOW_WRITE", "Process")

Push-Location $ProjectRoot
try {
    Write-Host "1/4 Desplegando staging..." -ForegroundColor Cyan
    & ".\scripts\deploy-staging.ps1" -EnvFile $EnvFile -SkipBuild:$EffectiveSkipBuild
    Assert-LastExitCode "El despliegue de staging fallo."

    Write-Host "2/4 Validando contenedores y endpoints..." -ForegroundColor Cyan
    & ".\scripts\validate-staging.ps1" -BaseUrl $BaseUrl -EnvFile $EnvFile
    Assert-LastExitCode "La validacion de salud de staging fallo."

    Write-Host "3/4 Creando cuentas tecnicas temporales..." -ForegroundColor Cyan
    & docker compose @ComposeArgs exec -T `
        -e VINOVA_ENVIRONMENT=staging `
        -e VINOVA_SMOKE_ALLOW_ROLE_PROVISION=true `
        web python manage.py deployment_smoke_roles provision `
        --run-id $RunId `
        --output $ContainerManifest `
        --expires-hours 4
    Assert-LastExitCode "No se pudieron crear las cuentas temporales del bot."
    $Provisioned = $true

    $ManifestLines = @(& docker compose @ComposeArgs exec -T web cat $ContainerManifest)
    Assert-LastExitCode "No se pudo leer el manifest temporal del bot desde app_run."
    $ManifestJson = ($ManifestLines | ForEach-Object { [string]$_ }) -join "`n"
    if ([string]::IsNullOrWhiteSpace($ManifestJson)) {
        throw "El manifest temporal del bot fue creado vacio."
    }
    try {
        $Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($LocalManifest, $ManifestJson, $Utf8NoBom)
        $Manifest = $ManifestJson | ConvertFrom-Json
    }
    catch {
        throw "El manifest temporal del bot no contiene JSON valido: $($_.Exception.Message)"
    }
    $AdminAccount = $Manifest.accounts.admin_general
    if (-not $AdminAccount -or -not $AdminAccount.username -or -not $AdminAccount.password) {
        throw "El bot no genero una cuenta admin_general valida."
    }

    [Environment]::SetEnvironmentVariable("VINOVA_SMOKE_USERNAME", [string]$AdminAccount.username, "Process")
    [Environment]::SetEnvironmentVariable("VINOVA_SMOKE_PASSWORD", [string]$AdminAccount.password, "Process")
    [Environment]::SetEnvironmentVariable("VINOVA_SMOKE_ALLOW_WRITE", $(if ($ReadOnly) { "false" } else { "true" }), "Process")

    $Timeout = Read-EnvValue "VINOVA_SMOKE_TIMEOUT"
    if (-not $Timeout) { $Timeout = "30" }
    $Retries = Read-EnvValue "VINOVA_SMOKE_RETRIES"
    if (-not $Retries) { $Retries = "1" }

    $SmokeArguments = @(
        $BaseUrl,
        "--mode", "staging",
        "--username", [string]$AdminAccount.username,
        "--password", [string]$AdminAccount.password,
        "--role-credentials-file", $LocalManifest,
        "--timeout", $Timeout,
        "--retries", $Retries
    )
    if ($ReadOnly) {
        foreach ($Scenario in @("tls", "public", "auth", "health", "assets", "navigation", "security", "roles", "accessibility")) {
            $SmokeArguments += @("--scenario", $Scenario)
        }
    }
    else {
        $SmokeArguments += @("--scenario", "all", "--write-tests", "--cleanup")
    }

    $Uri = [System.Uri]$BaseUrl
    if ($Uri.Scheme -eq "https" -and $Uri.Host -in @("localhost", "127.0.0.1", "::1")) {
        $SmokeArguments += "--insecure-local-tls"
    }

    Write-Host "4/4 Ejecutando el Deployment Smoke Bot completo..." -ForegroundColor Cyan
    & ".\scripts\qa-deployment-smoke.ps1" @SmokeArguments
    Assert-LastExitCode "El Deployment Smoke Bot encontro fallos."

    Write-Host "" 
    Write-Host "Staging aprobado por el bot: infraestructura, login, permisos por rol y flujos funcionales." -ForegroundColor Green
    Write-Host "Las cuentas tecnicas son temporales y se desactivaran automaticamente."
}
finally {
    if ($Provisioned) {
        Write-Host "Desactivando cuentas tecnicas temporales..." -ForegroundColor DarkGray
        & docker compose @ComposeArgs exec -T `
            -e VINOVA_ENVIRONMENT=staging `
            -e VINOVA_SMOKE_ALLOW_ROLE_PROVISION=true `
            web python manage.py deployment_smoke_roles disable `
            --run-id $RunId | Out-Host
        & docker compose @ComposeArgs exec -T web sh -lc "rm -f '$ContainerManifest'" | Out-Null
    }
    Remove-Item -LiteralPath $LocalManifest -Force -ErrorAction SilentlyContinue
    [Environment]::SetEnvironmentVariable("VINOVA_SMOKE_USERNAME", $PreviousSmokeUser, "Process")
    [Environment]::SetEnvironmentVariable("VINOVA_SMOKE_PASSWORD", $PreviousSmokePassword, "Process")
    [Environment]::SetEnvironmentVariable("VINOVA_SMOKE_ALLOW_WRITE", $PreviousAllowWrite, "Process")
    Pop-Location
}
