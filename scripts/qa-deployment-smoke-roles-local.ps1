# ES: Ejecuta el flujo operativo «qa deployment smoke roles local» con fallos controlados y sin ocultar errores.
# EN: Runs the «qa deployment smoke roles local» operational flow with controlled failures and visible errors.
[CmdletBinding()]
param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [ValidateSet("chromium", "firefox", "webkit")]
    [string]$Browser = "chromium"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
# ES: La sección siguiente define precondiciones, límites y propagación explícita de fallos.
# EN: The following section defines preconditions, limits, and explicit failure propagation.

$RunId = ([guid]::NewGuid().ToString("N")).Substring(0, 12)
$ContainerManifest = "/tmp/vinova-smoke-roles-$RunId.json"
$LocalManifest = Join-Path $env:TEMP "vinova-smoke-roles-$RunId.json"
$VenvPython = Join-Path $ProjectRoot ".venv-smoke\Scripts\python.exe"
$Python = if ($env:VINOVA_SMOKE_PYTHON) {
    $env:VINOVA_SMOKE_PYTHON
} elseif (Test-Path $VenvPython) {
    $VenvPython
} else {
    "python"
}
$ExitCode = 1

try {
    docker compose exec -T `
        -e VINOVA_ENVIRONMENT=local `
        -e VINOVA_SMOKE_ALLOW_ROLE_PROVISION=true `
        web python manage.py deployment_smoke_roles provision `
        --run-id $RunId `
        --output $ContainerManifest

    if ($LASTEXITCODE -ne 0) {
        throw "No se pudieron crear las cuentas temporales de roles."
    }

    docker compose cp "web:$ContainerManifest" $LocalManifest
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $LocalManifest)) {
        throw "No se pudo copiar el manifest temporal de roles."
    }

    & $Python "scripts/run_deployment_smoke.py" `
        $BaseUrl `
        --allow-http-local `
        --scenario roles `
        --browser $Browser `
        --role-credentials-file $LocalManifest
    $ExitCode = $LASTEXITCODE
}
finally {
    docker compose exec -T `
        -e VINOVA_ENVIRONMENT=local `
        -e VINOVA_SMOKE_ALLOW_ROLE_PROVISION=true `
        web python manage.py deployment_smoke_roles disable `
        --run-id $RunId | Out-Host

    docker compose exec -T web sh -lc "rm -f '$ContainerManifest'" | Out-Null
    Remove-Item $LocalManifest -Force -ErrorAction SilentlyContinue
}

exit $ExitCode
