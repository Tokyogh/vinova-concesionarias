# Operación de Vinova Pro 2.0.0

## Diario

- Revisar `/health/live/`, `/health/ready/` y `/health/dependencies/`.
- Revisar errores de aplicación, colas Celery, tareas fallidas, capacidad de disco y alertas de seguridad.
- Confirmar que web, PostgreSQL, Redis, worker y beat estén saludables.
- Revisar solicitudes Staff pendientes/expiradas y entregas webhook fallidas sin exponer IP, hashes ni secretos.

## Semanal

- Verificar backups, checksum, copia externa y crecimiento de PostgreSQL.
- Revisar cuentas inactivas, asignaciones temporales y certificados próximos a vencer.
- Revisar aprobaciones Staff temporales, cambios de CIDR, versiones de consentimiento y proveedores opcionales.
- Ejecutar el smoke de lectura en staging después de cambios operativos.

## Mensual

- Restaurar un backup en entorno aislado.
- Revisar privilegios globales, retención, capacidad y dependencias pendientes.
- Regenerar/auditar lock y SBOM cuando cambien dependencias; revisar digests y escaneo de imágenes.
- Ensayar restore aislado midiendo RPO/RTO; no automatizar purga local sin copia externa verificable.
- Aplicar actualizaciones primero en staging siguiendo [ACTUALIZACION.md](ACTUALIZACION.md).

## Incidentes

1. Preservar logs y auditoría.
2. Contener el impacto sin borrar datos ni volúmenes.
3. Aplicar rollback lógico si corresponde.
4. Validar healthchecks y smoke.
5. Documentar causa, alcance, recuperación y prevención.

Para pérdida o corrupción de datos, siga [EMERGENCY_RECOVERY.md](EMERGENCY_RECOVERY.md).
Para desactivar una política Staff que bloquee la recuperación, use solo el
procedimiento auditado de [acceso Staff adaptativo](seguridad-avanzada/08-acceso-staff-adaptativo.md).
