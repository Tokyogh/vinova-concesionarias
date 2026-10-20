# ES: Ejecuta el flujo operativo «validate release» con fallos controlados y sin ocultar errores.
# EN: Runs the «validate release» operational flow with controlled failures and visible errors.
param(
    [string]$PythonBin = "python",
    [string]$Settings = "config.settings.test",
    [string]$SchemaOutput = "$env:TEMP\vinova-pro-v2.0.0-openapi.yaml"
)

$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param([Parameter(Mandatory = $true)][string[]]$CommandArgs)
    & $PythonBin @CommandArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Falló: $PythonBin $($CommandArgs -join ' ')"
    }
}

Invoke-Checked -CommandArgs @("-m", "ruff", "check", ".")
Invoke-Checked -CommandArgs @("manage.py", "check", "--settings=$Settings")
Invoke-Checked -CommandArgs @("manage.py", "makemigrations", "--check", "--dry-run", "--settings=$Settings")
Invoke-Checked -CommandArgs @("manage.py", "check_release_readiness", "--strict", "--settings=$Settings")
Invoke-Checked -CommandArgs @(
    "manage.py", "spectacular", "--urlconf", "apps.api.schema_urls", "--validate", "--file", $SchemaOutput,
    "--settings=$Settings"
)
Invoke-Checked -CommandArgs @("-m", "pytest", "-q")

Write-Host "Validación estática y Django/Pytest de Vinova Pro v2.0.0 completada."
Write-Host "Esquema OpenAPI temporal: $SchemaOutput"
