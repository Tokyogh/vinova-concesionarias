# Cierre integral de VINOVA LITE → VINOVA PRO

- Fecha de corte: 2026-10-09
- Rama: `integration/lite-pro`
- Base auditada: `d39d15d`
- Bloques ejecutados: B0-B9 y B11
- Bloque B10: omitido por falta de autorización explícita para importar datos históricos

## Resultado

La integración obligatoria queda cerrada en código. PRO conserva su arquitectura empresarial y recupera el portal útil de LITE sin duplicar sus modelos ni copiar sus patrones inseguros. `web_carros/` permaneció como referencia de solo lectura.

Quedaron integrados el alta segura, portal y perfil, garaje, imágenes autorizadas, servicios e historial, documentos, facturas, notificaciones, preferencias, navegación transversal y almacenamiento de producción. No se añadió multi-tenancy, no se modificó SRI y no se crearon recordatorios automáticos.

## Bloques y commits

| Bloque | Commit | Entrega |
|---|---|---|
| B0 | `ab2a403` | Ownership, garaje y canje estabilizados |
| B1 | `86b9b57` | Alta, invitación y recuperación de cliente |
| B2 | `264d7cc` | Shell, dashboard y perfil privados |
| B3 | `3ede3e6` | Garaje digital privado |
| B4 | `89a031a` | Historial y operación de posventa |
| B5 | `71f7559` | Biblioteca documental privada |
| B6 | `b8ee12d` | Facturas y PDF privado |
| B7 | `4731d00` | Bandeja y preferencias de notificación |
| B8 | `e84eddd` | Integración UX, accesibilidad y rendimiento |
| B9 | `b224d64` | Cloudinary y storage S3-compatible |
| B11 | commit de cierre de esta entrega | Regresión, seguridad, E2E, restore drill y documentación |

## Evidencia de aceptación

| Control | Resultado |
|---|---|
| Suite Django sin los 3 casos exclusivos de PostgreSQL | 2.407 aprobadas, 37 omitidas, 0 fallos |
| E2E Chromium, 11 escenarios | 32 aprobadas, 0 fallos, 0 omitidas |
| Escenarios E2E focales corregidos | clientes/roles 3/3; autenticación 5/5; portal 1/1 |
| Contratos del arnés E2E | 29 aprobados |
| Seguridad/performance/portal focal previa | 1.796 aprobadas, 3 omitidas |
| Ruff | limpio |
| `manage.py check` | 0 incidencias |
| `makemigrations --check --dry-run` | sin cambios |
| Migraciones del restore drill | 74 aplicadas, 0 pendientes |

El conjunto horizontal cubre Customer A/B, cliente frente a Staff, permiso de portal sin Customer, rol vencido, transferencia de unidad, módulo de posventa deshabilitado, archivos privados, CSRF, rate limit y rutas directas. El acceso requiere simultáneamente permiso vigente y expediente Customer activo; conocer un identificador o URL no concede ownership.

La E2E final incluye público, autenticación, vehículos, clientes, inventario, ventas/facturación, documentos, seguridad/continuidad, 13 roles, responsive/accesibilidad y portal. El ejecutor `all` y sus wrappers PowerShell/Bash enumeran ya los once escenarios.

## Restore drill

Se ejecutó un ensayo funcional aislado con SQLite bajo `config.settings.test`; no tocó datos de desarrollo ni producción.

- Backup: `ea398ca5-f716-49e0-a491-323093e92b3f`.
- Formato: v3.
- SHA-256: `79cb455e21b68e9a8ce14b0efdd4027e27fecf0504d19633a193509ceef6b0ab`.
- Verificación: archivo, manifiesto, inventario y compatibilidad aprobados.
- Extracción: destino nuevo y vacío; `manifest.json` y `database.sqlite3` presentes.
- Estado de esquema: actual, 74 migraciones aplicadas y ninguna pendiente.

La restauración real debe ensayarse nuevamente con PostgreSQL y una copia de los objetos externos antes de promover la versión. El procedimiento oficial continúa en `docs/BACKUPS.md` y `docs/EMERGENCY_RECOVERY.md`.

## Gates externos previos a producción

No son defectos de código cerrables sin infraestructura o credenciales reales:

1. Ejecutar en PostgreSQL `apps/leads/tests/test_conversion_concurrency_v110.py`. En este cierre Docker Desktop no respondió y `localhost:5432` estaba cerrado; por eso esos tres casos se excluyeron de la cifra final local. Los bloques anteriores sí registran validaciones PostgreSQL focales.
2. Ejecutar `check_storage_integrations --live` en staging y completar crear/consultar/reemplazar/borrar de avatar Cloudinary.
3. Completar save/open/URL firmada/delete en el bucket S3-compatible privado de staging y comprobar que no exista acceso público.
4. Ejecutar smoke del candidato desplegado, TLS, correo, Celery/Redis, backup PostgreSQL y restore aislado.
5. Hacer revisión humana final de escritorio, tablet y móvil con datos representativos.

## Checklist de despliegue

1. Revisar `.env` productivo, secretos, dominios, CSRF, SMTP, Cloudinary y storage privado; no reutilizar secretos de QA.
2. Crear y verificar un backup completo; registrar imagen, commit y versión actualmente desplegados.
3. Ejecutar gates externos anteriores y conservar sus reportes fuera del repositorio.
4. Construir el candidato y ejecutar checks estrictos, migraciones y seeds idempotentes de roles, scopes y ayuda.
5. Confirmar `/health/live/`, `/health/ready/`, Celery, colas, descargas privadas y flujos críticos del portal.
6. Ejecutar el smoke de despliegue con una cuenta QA enlazada a un Customer sintético, nunca con datos personales reales.
7. Abrir tráfico solo después de revisar logs, permisos por sucursal y métricas de error.

## Rollback

1. Detener la promoción y preservar logs, artefactos, volúmenes y el backup verificado.
2. Retirar tráfico de la versión defectuosa sin borrar volúmenes.
3. Restaurar la imagen/commit anterior y comprobar compatibilidad de esquema.
4. Si hay incompatibilidad o corrupción, preparar el backup en un entorno aislado, validar aplicación y datos, y recién entonces ejecutar la restauración operativa aprobada.
5. Repetir healthchecks y smoke antes de devolver tráfico.

No usar `migrate app zero`, `docker compose down -v`, force push ni restauración directa sobre producción como atajo de rollback.

## Exclusiones preservadas

- `web_carros/` no fue modificado.
- No se importaron datos LITE ni se ejecutó B10.
- No se cambió ni conectó el módulo SRI desde esta integración.
- No se añadieron recordatorios automáticos, schedulers ni campañas de mantenimiento.
- No se copiaron floats monetarios, SQL crudo, open redirects, URLs privadas públicas ni guards por prefijo de LITE.
- El catálogo público de repuestos y el mapa ampliado de sedes permanecen como mejoras P3 separadas; no bloquean el portal privado.
