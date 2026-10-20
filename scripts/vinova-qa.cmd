@echo off
REM ES: Ejecuta el flujo operativo vinova qa con fallos controlados y sin ocultar errores.
REM EN: Runs the vinova qa operational flow with controlled failures and visible errors.
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PROFILE=%~1"
if "%PROFILE%"=="" set "PROFILE=quick"

if /I not "%PROFILE%"=="quick" if /I not "%PROFILE%"=="full" if /I not "%PROFILE%"=="release" (
  echo Uso: scripts\vinova-qa.cmd [quick^|full^|release]
  exit /b 2
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0vinova-qa.ps1" -Profile "%PROFILE%"
exit /b %ERRORLEVEL%
