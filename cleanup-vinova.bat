@echo off
REM ES: Ejecuta el flujo operativo «cleanup vinova» con fallos controlados y sin ocultar errores.
REM EN: Runs the «cleanup vinova» operational flow with controlled failures and visible errors.
setlocal EnableExtensions EnableDelayedExpansion

rem ============================================================
rem VINOVA PRO - LIMPIEZA SEGURA DE BASURA Y REPORTES QA
rem
rem Uso:
rem   cleanup-vinova.bat
rem       Solo muestra lo que se eliminaria.
rem
rem   cleanup-vinova.bat --delete
rem       Elimina los elementos encontrados.
rem
rem Colocar este archivo en la raiz del proyecto, junto a:
rem   manage.py
rem   docker-compose.yml
rem   README.md
rem ============================================================

cd /d "%~dp0"

set "MODE=PREVIEW"
if /I "%~1"=="--delete" set "MODE=DELETE"

echo.
echo ============================================================
echo VINOVA PRO - LIMPIEZA SEGURA
echo Proyecto: %CD%
echo Modo: %MODE%
echo ============================================================
echo.

if not exist "manage.py" (
    echo [ERROR] No se encontro manage.py.
    echo Coloca este archivo en la raiz del proyecto.
    exit /b 1
)

echo [INFO] Este script NO elimina:
echo        apps\reports
echo        apps
echo        config
echo        templates
echo        static
echo        docs
echo        migrations
echo        archivos .env.example
echo        archivos de codigo fuente
echo.

rem ------------------------------------------------------------
rem Directorios conocidos de entorno, cache y reportes generados
rem ------------------------------------------------------------

call :ProcessDir ".venv"
call :ProcessDir ".venv-smoke"
call :ProcessDir "venv"
call :ProcessDir "env"
call :ProcessDir "node_modules"
call :ProcessDir "staticfiles"
call :ProcessDir ".pytest_cache"
call :ProcessDir ".ruff_cache"
call :ProcessDir ".mypy_cache"
call :ProcessDir ".tox"
call :ProcessDir "htmlcov"
call :ProcessDir "coverage_html"
call :ProcessDir "playwright-report"
call :ProcessDir "test-results"
call :ProcessDir "qa-reports"
call :ProcessDir "qa_reports"
call :ProcessDir "reports\qa"
call :ProcessDir "private\qa_reports"
call :ProcessDir "deployment\runtime"
call :ProcessDir "logs"
call :ProcessDir "tmp"
call :ProcessDir "temp"
call :ProcessDir ".cache"

rem ------------------------------------------------------------
rem Directorios recursivos de cache Python
rem ------------------------------------------------------------

for /d /r %%D in (__pycache__) do (
    if exist "%%~fD" call :ProcessDir "%%~fD"
)

for /d /r %%D in (.pytest_cache) do (
    if exist "%%~fD" call :ProcessDir "%%~fD"
)

for /d /r %%D in (.ruff_cache) do (
    if exist "%%~fD" call :ProcessDir "%%~fD"
)

rem ------------------------------------------------------------
rem Archivos temporales y caches conocidos
rem ------------------------------------------------------------

call :ProcessFile ".coverage"
call :ProcessFile "coverage.xml"
call :ProcessFile "celerybeat-schedule"
call :ProcessFile "celerybeat-schedule.db"
call :ProcessFile "db.sqlite3"
call :ProcessFile "test.sqlite3"
call :ProcessFile "npm-debug.log"
call :ProcessFile "yarn-error.log"
call :ProcessFile "Thumbs.db"
call :ProcessFile "desktop.ini"

rem ------------------------------------------------------------
rem Reportes QA generados en la raiz
rem Solo patrones especificos para no tocar apps\reports
rem ------------------------------------------------------------

for %%F in (
    "qa-*.json"
    "qa-*.html"
    "qa-*.zip"
    "qa_*.json"
    "qa_*.html"
    "qa_*.zip"
    "summary-qa-*.json"
    "summary_qa_*.json"
    "pytest-report*.xml"
    "pytest-report*.html"
    "junit*.xml"
    "coverage*.json"
) do (
    for %%G in (%%F) do (
        if exist "%%~fG" call :ProcessFile "%%~fG"
    )
)

rem ------------------------------------------------------------
rem Archivos Python compilados y temporales de editor
rem ------------------------------------------------------------

for /r %%F in (*.pyc *.pyo *.tmp *.bak *~) do (
    if exist "%%~fF" call :ProcessFile "%%~fF"
)

echo.
echo ============================================================
if /I "%MODE%"=="PREVIEW" (
    echo REVISION COMPLETADA.
    echo No se elimino ningun archivo.
    echo.
    echo Para borrar realmente, ejecuta:
    echo   cleanup-vinova.bat --delete
) else (
    echo LIMPIEZA COMPLETADA.
    echo Revisa ahora:
    echo   git status --short
)
echo ============================================================
echo.

exit /b 0


REM ES: La sección siguiente valida precondiciones y propaga códigos de error.
REM EN: The following section validates preconditions and propagates error codes.
:ProcessDir
set "TARGET=%~1"
if not exist "%TARGET%\" exit /b 0

if /I "%MODE%"=="PREVIEW" (
    echo [BORRARIA DIRECTORIO] %TARGET%
) else (
    echo [ELIMINANDO DIRECTORIO] %TARGET%
    attrib -R -H -S "%TARGET%" /S /D >nul 2>&1
    rmdir /S /Q "%TARGET%" >nul 2>&1

    if exist "%TARGET%\" (
        echo [ADVERTENCIA] No se pudo eliminar completamente: %TARGET%
    )
)
exit /b 0


:ProcessFile
set "TARGET=%~1"
if not exist "%TARGET%" exit /b 0

if /I "%MODE%"=="PREVIEW" (
    echo [BORRARIA ARCHIVO] %TARGET%
) else (
    echo [ELIMINANDO ARCHIVO] %TARGET%
    attrib -R -H -S "%TARGET%" >nul 2>&1
    del /F /Q "%TARGET%" >nul 2>&1

    if exist "%TARGET%" (
        echo [ADVERTENCIA] No se pudo eliminar: %TARGET%
    )
)
exit /b 0
