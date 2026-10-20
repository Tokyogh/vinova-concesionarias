# Actualización y mantenimiento técnico

El contrato normativo de versiones, migraciones, upgrade y rollback está en `docs/LIFECYCLE.md`. Consulte el estado
real de la instalación con `python manage.py show_vinova_lifecycle --json`; no infiera el schema de base de datos a
partir de `VINOVA_PRODUCT_VERSION` ni trate el formato de backup/transfer como versión del producto.
La separación de privilegios, el manifest firmado y el flujo del agente externo están en
`docs/UPDATE_ARCHITECTURE.md`.

## Antes de actualizar

1. Probar el release en staging.
2. Crear y verificar un backup de base de datos y archivos privados.
3. Registrar la versión y la imagen actualmente desplegadas.
4. Revisar migraciones con `python manage.py migrate --plan`.
5. Confirmar que el release declara compatibilidad y una ruta de migración desde la versión instalada.
6. Verificar `requirements/production.lock` con `pip-audit`, construir con hashes y escanear las imágenes por digest.

## Actualización

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml run --rm web python manage.py migrate --noinput
docker compose -f docker-compose.prod.yml run --rm web python manage.py seed_roles
docker compose -f docker-compose.prod.yml run --rm web python manage.py seed_api_scopes
docker compose -f docker-compose.prod.yml run --rm web python manage.py seed_help_center
docker compose -f docker-compose.prod.yml up -d
```

No use `docker compose down -v`. Conserve `.env`, media, private, certificados, backups y volúmenes.

## Verificación

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py migrate --check
docker compose -f docker-compose.prod.yml exec web python manage.py check
docker compose -f docker-compose.prod.yml exec web python manage.py check_celery
```

Ejecute después el smoke de lectura. Si falla una migración, no altere manualmente la tabla ni marque la migración como aplicada: preserve logs y restaure primero en un entorno aislado.

El downgrade no está garantizado. El rollback soportado consiste en restaurar un backup verificado del conjunto
compatible de código, base y archivos; no en revertir migraciones a ciegas.

## Mantenimiento

- Actualice dependencias e imágenes de forma selectiva, con revisión de changelog, CVE, CISA KEV, EPSS, lock/hash, SBOM y regresión.
- Pruebe migraciones desde una base limpia y desde una copia restaurada.
- Rote credenciales mediante un procedimiento explícito; no cambie `SECRET_KEY` o `VINOVA_API_TOKEN_PEPPER` accidentalmente.
