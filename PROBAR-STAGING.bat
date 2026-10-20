@echo off
REM ES: Ejecuta el flujo operativo «PROBAR STAGING» con fallos controlados y sin ocultar errores.
REM EN: Runs the «PROBAR STAGING» operational flow with controlled failures and visible errors.
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0PROBAR-STAGING.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo El bot encontro un problema. Revise la salida y el evidence.zip mas reciente.
  pause
)
exit /b %EXIT_CODE%
