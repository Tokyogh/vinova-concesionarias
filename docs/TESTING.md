# Testing y calidad

| Capa | Herramienta | Demuestra |
|---|---|---|
| checks | Django y migration drift | configuración/esquema coherentes |
| lint | Ruff | errores estáticos del contrato configurado |
| unit/integration | Pytest + pytest-django | reglas, servicios, vistas, API y persistencia |
| RBAC/seguridad | D5/D7 y matriz integral | permisos, ownership, CSRF, inputs y exposición |
| navegador | Playwright | recorridos, responsive, accesibilidad y perfiles |
| mapas funcionales | Playwright + capturas anotadas | trazabilidad visual de rutas, datos, permisos y estados vacíos |
| PostgreSQL | DB aislada | locks, concurrencia, idempotencia y constraints |
| release | perfiles `quick/full/release` | gates reproducibles y evidencia privada |
| documentación | auditoría bilingüe y enlaces | cabeceras ES→EN, bloques internos y referencias válidas |

## Suite local aislada

```powershell
$env:DJANGO_SETTINGS_MODULE='config.settings.test'
$env:VINOVA_QA_IGNORE_PROJECT_ENV='1'
python manage.py check
python manage.py makemigrations --check --dry-run
python -m ruff check .
python scripts/audit_bilingual_documentation.py --strict
python -m pytest -q
```

La variable `VINOVA_QA_IGNORE_PROJECT_ENV=1` evita que `.env` contamine las
pruebas. `config.settings.test` usa roots temporales, caché local y SQLite salvo
que se proporcione `TEST_DATABASE_URL`.

## Perfiles dedicados

```text
scripts/qa-full.cmd       suite completa y Chromium
scripts/qa-release.cmd    gates de release
scripts/vinova-qa.cmd     CLI del runner aislado
docker-compose.qa.yml     PostgreSQL/Redis QA efímeros
docker-compose.qa-cli.yml ejecución standalone aislada
```

Los E2E requieren `VINOVA_E2E_ACTIVE=1` o los scripts. Los reportes quedan en
storage privado/runtime ignorado y deben redactar secretos.

El escenario `maps` genera las 15 capturas controladas de
[`mapas-funcionales/`](mapas-funcionales/README.md):

```powershell
.\scripts\qa-e2e.cmd maps chromium
```

Usa exclusivamente la base temporal E2E. Las leyendas se inyectan para la
captura y no alteran la interfaz persistida.

Las regresiones focales de seguridad cubren DNS/SSRF, 2FA, cookies/sesiones,
consentimiento, acceso Staff habitual/denegado/aprobado, límites de archivos,
RBAC, ownership y módulos OFF. Las pruebas de PostgreSQL y Chromium deben
ejecutarse en sus perfiles reales; no se cuentan como aprobadas por pasar SQLite.

Un gate solo se aprueba si se ejecutó sobre el commit candidato. Los skips se
clasifican; staging, TLS, proveedores y revisión humana son gates separados.

Resultados actuales: [checkpoint de auditoría](auditoria-integral/ESTADO_ACTIVO.md).
