@echo off
REM ES: Ejecuta el flujo operativo «qa deployment smoke roles local» con fallos controlados y sin ocultar errores.
REM EN: Runs the «qa deployment smoke roles local» operational flow with controlled failures and visible errors.
setlocal
set "SCRIPT_DIR=%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%qa-deployment-smoke-roles-local.ps1" %*
exit /b %ERRORLEVEL%
