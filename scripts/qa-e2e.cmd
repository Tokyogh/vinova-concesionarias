@echo off
REM ES: Ejecuta el flujo operativo qa e2e con fallos controlados y sin ocultar errores.
REM EN: Runs the qa e2e operational flow with controlled failures and visible errors.
setlocal EnableExtensions DisableDelayedExpansion
set "VINOVA_E2E_RAW_ARGS=%*"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0qa-e2e.ps1"
set "VINOVA_E2E_EXIT_CODE=%ERRORLEVEL%"
endlocal & exit /b %VINOVA_E2E_EXIT_CODE%
