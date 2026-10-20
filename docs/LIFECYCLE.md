# Lifecycle y compatibilidad de VINOVA PRO

Estado: **IMPLEMENTED / VERIFIED (foundation N11)**.

## Identificadores independientes

VINOVA no usa un único número para describir todo el estado de una instalación:

- `VINOVA_PRODUCT_VERSION`: release del software que ejecuta el servidor.
- `database_migration_state`: ledger real de migraciones Django aplicadas y pendientes, con fingerprint SHA-256.
- `VINOVA_BACKUP_FORMAT_VERSION`: formato del archivo de recuperación; actualmente `3` (lector compatible con `2`).
- `VINOVA_TRANSFER_FORMAT_VERSION`: contrato futuro de portabilidad de una instalación; actualmente `1`.

Que dos valores coincidan accidentalmente no los convierte en el mismo concepto. El dataset de integraciones también
mantiene su propio `schema_version` y no forma parte del lifecycle de instalación.

El estado verificable se consulta sin mutar la instalación:

```bash
python manage.py show_vinova_lifecycle
python manage.py show_vinova_lifecycle --json
```

El fingerprint representa el ledger de migraciones aplicado; no afirma por sí solo que el schema físico no haya sido
alterado manualmente.

## Contrato de upgrade

La dirección principal es forward-only. Un upgrade sólo puede habilitarse cuando se cumplen ambas condiciones:

1. el release declara compatibilidad con la versión instalada;
2. existe una ruta de migración verificada hasta la versión objetivo.

Comparar `2.0.0 < 3.0.0` no basta para autorizar el despliegue. Incluso cuando el contrato permite avanzar, el flujo
requiere preflight y un backup verificado antes de entrar en mantenimiento. Las versiones de producto usan SemVer
estable `MAJOR.MINOR.PATCH`; los canales prerelease futuros deben añadir un contrato explícito y no reutilizar cadenas
ambiguas.

## Rollback y downgrade

El downgrade de código y migraciones no está garantizado ni se presenta como seguro. Ante un fallo crítico:

- detener el despliegue;
- preservar logs y artefactos;
- usar el backup pre-update verificado;
- restaurar código, base y archivos como un conjunto compatible;
- validar el restore en infraestructura aislada antes de reemplazar producción.

Rollback significa restaurar un estado completo conocido, no ejecutar migraciones inversas a ciegas.

## Boundary operativo

Los empleados no actualizan clientes locales: VINOVA es una aplicación web y se actualiza el servidor de la
instalación single-tenant. Django puede exponer estado y ejecutar comprobaciones no privilegiadas, pero no recibe
root, acceso irrestricto a Docker ni responsabilidad directa sobre el despliegue. Ese boundary se desarrolla en N13.
