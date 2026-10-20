# F12 — Disponibilidad, archivos y recuperación

Fecha de evidencia local: 2026-10-16

## Resultado

La revisión local confirma controles operativos para colas, almacenamiento privado, backups y recuperación, y cierra dos riesgos de agotamiento de recursos reproducibles: contenedores ZIP/Office sin límites de expansión e importaciones CSV/XLSX sin límites de filas o columnas. No se declara continuidad productiva: el restore real, los proveedores externos, la observabilidad remota y el antivirus/CDR siguen siendo gates externos.

## Controles verificados

| Superficie | Estado local | Evidencia principal |
|---|---|---|
| backups | formato 3 con inventario, tamaño y SHA-256 por archivo; publicación atómica desde `.partial`; errores auditados | `apps/continuity/services.py`, pruebas de continuidad |
| restauración | verificación de integridad/compatibilidad, extracción aislada, destino vacío y preflight de espacio libre | `prepare_vinova_restore`, pruebas de restore/transfer |
| colas y Celery | colas separadas, `acks_late`, rechazo si muere el worker, prefetch 1, límites de tiempo, rate limit y retry acotado | settings, dispatch, tareas y `check_celery` |
| readiness | base, caché, storages y heartbeat Celery opcional; respuestas públicas mínimas | `apps/common/health.py` y regresiones DevOps |
| logging/alertas | JSON con redacción; fallos de auditoría observables; Sentry configurable | settings y suites de logging/auditoría |
| storage privado | raíz separada o S3-compatible, URL firmada, timeouts y health check | `apps/documents/storage.py` y sus pruebas |
| archivos | allowlist, tamaño, firma/contenedor, nombres internos y límites ZIP | `apps/common/validators.py` |
| importaciones | CSV/XLSX limitados a 10.000 filas y 100 columnas por defecto; XLSX en modo lectura; links externos deshabilitados | `apps/imports/parsing.py` y regresiones |
| backups/transfers comprimidos | máximo configurable de miembros y bytes descomprimidos; inventario y rutas validadas antes de extraer | `apps/continuity/archive.py` |

## Límites añadidos

Los valores son configurables y Django rechaza valores menores que uno mediante `vinova.E004`:

- `VINOVA_ZIP_MAX_ENTRIES=1000`;
- `VINOVA_ZIP_MAX_UNCOMPRESSED_MB=100`;
- `VINOVA_ZIP_MAX_COMPRESSION_RATIO=200`;
- `VINOVA_IMPORT_MAX_ROWS=10000`;
- `VINOVA_IMPORT_MAX_COLUMNS=100`;
- `VINOVA_ARCHIVE_MAX_MEMBERS=100000`;
- `VINOVA_ARCHIVE_MAX_UNCOMPRESSED_MB=51200`.

Los ZIP se inspeccionan sin extraer. Se rechazan miembros cifrados, rutas absolutas o con traversal, barras invertidas, caracteres de control, nombres duplicados incluso por diferencias de mayúsculas, exceso de miembros, expansión total excesiva y ratios de compresión anómalos. Un lote de importación rechazado se revierte y elimina únicamente el archivo recién recibido para no conservar residuos privados.

Los límites de archivo deben ajustarse con métricas de staging y capacidad real; elevarlos no sustituye cuotas, aislamiento ni protección a nivel proxy.

## Recuperación y retención

- El backup local no sustituye una copia externa cifrada, versionada y protegida contra borrado.
- `retention_days` expresa la política, pero VINOVA no elimina automáticamente backups locales: no existe evidencia persistente de copia externa que permita purgar con seguridad. La retención debe aplicarse en el proveedor y revisarse antes de automatizar borrado local.
- La preparación de restore nunca reemplaza datos activos. Requiere frase de confirmación, directorio vacío, integridad válida, versión compatible y al menos el doble del tamaño inventariado como espacio libre.
- RPO, RTO, capacidad, alertas y restore deben aprobarse mediante un ejercicio sobre infraestructura candidata. Las pruebas locales no demuestran tiempos productivos.

## Antivirus y CDR

No existe motor antivirus/CDR integrado. Extensión, firma, estructura, tamaño y storage privado reducen exposición, pero no detectan contenido malicioso conocido dentro de PDF, Office u otros formatos. `v5.0.0-5.4.3` permanece **No cumple**.

Antes de producción se debe seleccionar un motor o proveedor, mantener el objeto en cuarentena, escanearlo fuera del proceso web, bloquear publicación/descarga hasta resultado seguro, definir timeout/retry/fallo cerrado, registrar versión de firmas y resultado, y establecer tratamiento para falsos positivos. Si el formato y el caso de uso lo permiten, evaluar CDR además de antivirus. No se simuló esta evidencia.

## ASVS y riesgos residuales

- `v5.0.0-5.2.3` pasa a **Cumple verificado** por límites previos a extracción en ZIP/Office y regresiones de miembros/tamaño/ratio.
- `v5.0.0-5.4.3` permanece **No cumple** por ausencia de antivirus/CDR.
- Los requisitos generales de disponibilidad continúan conservadores cuando dependen de cuotas distribuidas, infraestructura, monitoreo externo o carga real.
- TAR.GZ de continuidad se limita y valida antes de extracción, pero su origen debe seguir siendo confiable y su hash debe verificarse; no es un canal público de upload.
- PDF, imagen, CSV y XLSX todavía requieren sandbox/antivirus según riesgo, además de los límites ya aplicados.

## Gates externos pendientes

1. Backup y restore PostgreSQL/S3 reales con medición de RPO/RTO y rollback.
2. Failover, capacidad, timeouts y alertas de Redis/Celery/Gunicorn/Nginx bajo carga autorizada.
3. Ciclos de lectura, firma, expiración y borrado sobre S3/Cloudinary reales.
4. Sink externo de logs/Sentry con TLS, redacción, alerta y retención verificadas.
5. Antivirus/CDR o cuarentena desplegados y probados con archivos benignos y corpus de prueba autorizado.

No se ejecutaron cargas destructivas ni operaciones sobre proveedores o producción.
