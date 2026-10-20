# ES: Ejecuta el flujo operativo «cleanup obsolete qa» con fallos controlados y sin ocultar errores.
# EN: Runs the «cleanup obsolete qa» operational flow with controlled failures and visible errors.
param()

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ObsoleteFiles = @(
    "tests\e2e\test_functional_flows.py",
    "scripts\vinova-e2e.cmd",
    "scripts\vinova-e2e.ps1",
    "scripts\vinova-e2e.sh",
    "test.sqlite3",
    "celerybeat-schedule"
)
$RegenerableDirectories = @(
    ".pytest_cache",
    ".ruff_cache",
    "staticfiles",
    "run\qa"
)

foreach ($Relative in $ObsoleteFiles) {
    $Path = Join-Path $ProjectRoot $Relative
    if (Test-Path $Path -PathType Leaf) {
        Remove-Item -Force $Path
        Write-Host "Eliminado: $Relative"
    }
}
foreach ($Relative in $RegenerableDirectories) {
    $Path = Join-Path $ProjectRoot $Relative
    if (Test-Path $Path -PathType Container) {
        Remove-Item -Recurse -Force $Path
        Write-Host "Eliminado: $Relative"
    }
}
Get-ChildItem -Path $ProjectRoot -Directory -Recurse -Force -Filter "__pycache__" -ErrorAction SilentlyContinue |
    ForEach-Object {
        Remove-Item -Recurse -Force $_.FullName
        Write-Host "Eliminado: $($_.FullName)"
    }

Write-Host "Limpieza QA terminada. No se modificaron .env, media, private, backups ni volúmenes Docker."
