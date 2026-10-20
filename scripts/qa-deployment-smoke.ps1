# ES: Ejecuta el flujo operativo «qa deployment smoke» con fallos controlados y sin ocultar errores.
# EN: Runs the «qa deployment smoke» operational flow with controlled failures and visible errors.
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$SmokeArguments
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$VenvPython = Join-Path $ProjectRoot ".venv-smoke\Scripts\python.exe"
$Python = if ($env:VINOVA_SMOKE_PYTHON) {
    $env:VINOVA_SMOKE_PYTHON
} elseif (Test-Path $VenvPython) {
    $VenvPython
} else {
    "python"
}
& $Python "scripts/run_deployment_smoke.py" @SmokeArguments
exit $LASTEXITCODE
