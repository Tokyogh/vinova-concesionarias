# ES: Ejecuta el flujo operativo «vinova qa» con fallos controlados y sin ocultar errores.
# EN: Runs the «vinova qa» operational flow with controlled failures and visible errors.
param(
    [ValidateSet("quick", "full", "release")]
    [string]$Profile = "quick"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
# ES: La sección siguiente define precondiciones, límites y propagación explícita de fallos.
# EN: The following section defines preconditions, limits, and explicit failure propagation.

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ProjectName = if ($env:VINOVA_QA_PROJECT_NAME) { $env:VINOVA_QA_PROJECT_NAME } else { "vinova-qa-cli" }
$ComposeFile = Join-Path $ProjectRoot "docker-compose.qa-cli.yml"
$ReportsDirectory = Join-Path $ProjectRoot "private\qa_reports"
$Compose = @("compose", "--project-name", $ProjectName, "-f", $ComposeFile)

Push-Location $ProjectRoot
try {
    New-Item -ItemType Directory -Force -Path $ReportsDirectory | Out-Null

    & docker info *> $null
    if ($LASTEXITCODE -ne 0) { throw "Docker Desktop no esta iniciado o el motor Docker no responde." }

    & docker @Compose config --quiet
    if ($LASTEXITCODE -ne 0) { throw "La configuracion de Docker Compose QA no es valida." }

    $RunnerImageName = "$ProjectName-qa_runner"
    & docker image inspect $RunnerImageName *> $null
    $RunnerImageExists = ($LASTEXITCODE -eq 0)
    if (-not $RunnerImageExists) {
        Write-Host "La imagen QA no existe; construyendo una sola vez..."
        & docker @Compose build qa_runner
        if ($LASTEXITCODE -ne 0) {
            Write-Host "La construccion fallo. El error real aparece en las lineas anteriores." -ForegroundColor Red
            throw "No se pudo construir la imagen QA."
        }
    }
    else {
        Write-Host "Reutilizando la imagen QA existente; el codigo actual se monta en modo solo lectura."
    }

    Write-Host "Iniciando PostgreSQL y Redis temporales..."
    & docker @Compose up -d --wait qa_db qa_redis
    if ($LASTEXITCODE -ne 0) {
        & docker @Compose ps --all
        & docker @Compose logs --tail=120 qa_db qa_redis
        throw "No se pudo iniciar la infraestructura QA. Revisa el diagnostico anterior."
    }

    $env:VINOVA_QA_PROFILE = $Profile
    & docker @Compose run --rm -e "VINOVA_QA_PROFILE=$Profile" qa_runner python scripts/vinova_qa.py --profile $Profile
    if ($LASTEXITCODE -ne 0) { throw "La validacion QA '$Profile' termino con errores." }
}
finally {
    try { & docker @Compose down --remove-orphans *> $null } catch {}
    Pop-Location
}
