# Procedimiento de emergencia y recuperación

## 1. Contener

- Detener escrituras si hay corrupción o incidente activo.
- No eliminar volúmenes.
- No ejecutar `docker compose down -v`.
- Conservar logs, auditoría y evidencia del incidente.

## 2. Identificar el backup

- Abrir `/dashboard/continuity/`.
- Elegir un backup completado o verificado.
- Confirmar fecha, tipo, tamaño y SHA-256.
- Verificar que exista una copia fuera del servidor.

## 3. Preparar un entorno aislado

```bash
docker compose run --rm web python manage.py verify_vinova_backup UUID
docker compose run --rm web python manage.py prepare_vinova_restore UUID --destination /tmp/vinova_restore --confirm PREPARE_RESTORE
```

No restaurar primero sobre producción.

## 4. Restaurar la base en pruebas

- Crear una base PostgreSQL temporal.
- Usar `pg_restore` con el archivo `database.dump` extraído.
- Configurar un `.env` exclusivo del entorno temporal.
- Ejecutar migraciones.

```bash
python manage.py migrate
python manage.py check
pytest -q
python manage.py verify_audit_integrity
```

## 5. Validar operación

- Login y permisos.
- Empresas y sucursales.
- Vehículos y catálogo.
- Clientes y CRM.
- Inventario y movimientos.
- Ventas y facturación.
- Documentos privados.
- Auditoría y alertas.
- Integridad de archivos y hashes.

## 6. Autorizar recuperación

La recuperación en producción debe tener:

- aprobación responsable;
- ventana de mantenimiento;
- backup del estado actual, incluso si está dañado;
- plan de reversión;
- responsables identificados;
- evidencia de la prueba realizada.

## 7. Cerrar

- Registrar el simulacro o incidente.
- Documentar tiempos, pérdidas y correcciones.
- Eliminar de forma segura los entornos temporales.
- Revisar la política y la frecuencia de backups.
