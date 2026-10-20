@echo off
REM ES: Ejecuta el flujo operativo qa release con fallos controlados y sin ocultar errores.
REM EN: Runs the qa release operational flow with controlled failures and visible errors.
call "%~dp0vinova-qa.cmd" release
exit /b %ERRORLEVEL%
