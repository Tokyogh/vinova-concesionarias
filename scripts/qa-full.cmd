@echo off
REM ES: Ejecuta el flujo operativo qa full con fallos controlados y sin ocultar errores.
REM EN: Runs the qa full operational flow with controlled failures and visible errors.
call "%~dp0vinova-qa.cmd" full
exit /b %ERRORLEVEL%
