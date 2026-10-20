@echo off
REM ES: Ejecuta el flujo operativo «CREAR ADMIN STAGING» con fallos controlados y sin ocultar errores.
REM EN: Runs the «CREAR ADMIN STAGING» operational flow with controlled failures and visible errors.
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0CREAR-ADMIN-STAGING.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" pause
exit /b %EXIT_CODE%
