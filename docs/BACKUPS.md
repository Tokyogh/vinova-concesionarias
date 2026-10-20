# Backups de Vinova Pro

## Flujo web asíncrono

Desde `/dashboard/continuity/` el registro pasa por:

```text
En cola → En ejecución → Completado/Verificado
                         ↘ Fallido
```

Se almacena el ID Celery, hora de encolado, modo de ejecución y cualquier fallo de publicación saneado. El archivo se construye con nombre temporal y solo se publica con su nombre final después de cerrar correctamente el TAR.GZ.

## Disponibilidad de Celery

En producción el fallback síncrono debe permanecer deshabilitado para evitar bloquear Gunicorn. Si la publicación al broker falla, investigue Redis y el worker antes de reintentar.

## Backup completo por comando

```bash
docker compose run --rm web python manage.py create_vinova_backup --type full
```

En producción:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py create_vinova_backup --type full
```

El comando es síncrono deliberadamente y registra `execution_mode=command`.

## Verificación

```bash
docker compose run --rm web python manage.py verify_vinova_backup UUID_DEL_BACKUP
```

El formato actual (`VINOVA_BACKUP_FORMAT_VERSION=3`) verifica el SHA-256 del contenedor, miembros permitidos,
manifest, inventario completo, tamaño y SHA-256 de cada archivo. El verificador sigue leyendo el formato 2 para no
invalidar backups existentes, pero los nuevos archivos usan formato 3. Integridad y compatibilidad de restore se
reportan por separado.

## Diagnóstico de cola

```bash
docker compose ps
docker compose logs redis
docker compose logs celery_worker
docker compose logs celery_beat
docker compose exec web python manage.py check_celery
docker compose exec celery_worker celery -A config inspect registered
```

Confirme que `apps.continuity.tasks.run_backup_task` esté registrada y que el Worker consuma la cola `backups`.

## Recuperación

Lea `docs/EMERGENCY_RECOVERY.md`. No restaure por primera vez sobre producción.

```bash
docker compose run --rm web python manage.py prepare_vinova_restore UUID --destination /tmp/vinova_restore --confirm PREPARE_RESTORE
```

El directorio debe estar vacío. Un backup de una versión anterior requiere además `--allow-forward-migration` y sólo
debe usarse cuando exista una ruta de migración verificada. Un backup de una versión futura se rechaza. La preparación
extrae en aislamiento; nunca reemplaza automáticamente la base o archivos activos. Antes de extraer comprueba los
límites configurados de miembros/bytes descomprimidos y exige espacio libre equivalente al doble del inventario.

## Transfer de instalación

Backup y transfer tienen propósitos y formatos distintos. Para mover una instalación use el flujo documentado en
`docs/TRANSFER.md`; un `.vinova` excluye credenciales, certificados, sesiones, reportes QA y backups anidados, que
deben reprovisionarse en el servidor destino.

## Copia externa

Una copia local no es suficiente. Use R2/S3/GCS u otro almacenamiento externo con cifrado, versionado, MFA para borrado, retención y pruebas de restore. No incluya `private/backups` dentro de sí mismo.

`BackupPolicy.retention_days` documenta la retención deseada, pero la aplicación no purga automáticamente archivos
locales porque todavía no registra una confirmación verificable de copia externa. Configure la retención en el proveedor
y no automatice el borrado local hasta disponer de esa evidencia y de un restore aprobado.
