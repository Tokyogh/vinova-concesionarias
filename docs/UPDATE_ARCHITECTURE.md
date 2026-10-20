# Arquitectura segura de actualizaciones VINOVA

Estado: **IMPLEMENTED / VERIFIED (N13 architecture and preflight)**. El despliegue privilegiado no está implementado
dentro de Django y no debe añadirse al request processing.

## Boundary obligatorio

```text
VINOVA Release Service          Servidor de la instalación
  manifest + artifact  --->    VINOVA Update Agent (host/deployment layer)
                                      |
                                      | estado saneado, sin secretos
                                      v
                               VINOVA Web / Update Center
```

- `web`, workers y beat siguen con filesystem read-only, `no-new-privileges` y `cap_drop: ALL`.
- Ningún contenedor de aplicación monta `/var/run/docker.sock` ni recibe root.
- El Update Agent vive fuera de Gunicorn/Django y es el único componente que puede coordinar el deployment layer.
- El Release Service distribuye metadata/artefactos; no recibe datos comerciales de concesionarias.
- El Update Center de N14 no añade un botón de actualización ni simula despliegues. Muestra versión y migration
  state locales, último backup verificado, health saneado y, únicamente si se configuran todos los archivos reales,
  el resultado del preflight firmado. El estado externo se consume desde un JSON acotado y con campos allowlisted.

## Contrato read-only del Update Center

La vista `/dashboard/continuity/updates/` exige el permiso global `continuity.view`. Lee estas rutas configuradas fuera
del repositorio: manifest, artefacto, clave pública confiable y estado del Update Agent. Si falta cualquiera de los
insumos del release, la UI declara `No disponible`; si son inválidos, falla cerrada y no expone rutas internas ni
excepciones. Los estados permitidos del agente son una allowlist y su archivo se limita a 128 KiB.

No hay endpoint web que active mantenimiento, despliegue, migraciones, reinicios o rollback. La navegación y la URL
directa comparten la autorización de continuidad, y ninguna preferencia de frontend amplía el acceso.

## Trust model del release

El manifest JSON usa schema `1`, producto `Vinova Pro`, versión SemVer estable, canal `stable|internal`, timestamp,
contrato `supported_from`, metadata del artefacto (`filename`, bytes, SHA-256) y firma Ed25519. La firma cubre la
serialización canónica del manifest sin el bloque `signature`.

La clave pública confiable y su `key_id` se configuran fuera del manifest. Un atacante no puede convertir una clave
propia en confiable incluyéndola junto al release. La rotación mantiene una allowlist temporal de IDs en el agente;
las claves privadas nunca llegan a instalaciones.

Validación local, no privilegiada:

```bash
python manage.py preflight_vinova_update release.json vinova-pro.tar.gz release-public.pem \
  --key-id release-2026
```

El comando sólo lee y diagnostica. No descarga, cambia mantenimiento, migra, reinicia ni despliega.

## Preflight fail-closed

Antes de autorizar al agente se requiere:

1. schema/product/canal conocidos;
2. firma Ed25519 con `key_id` confiable;
3. nombre, tamaño y SHA-256 exactos del artefacto;
4. versión instalada incluida en `supported_from` y ruta forward declarada;
5. ledger local sin migraciones pendientes;
6. backup de la versión instalada en estado `VERIFIED`;
7. PostgreSQL en producción;
8. espacio libre de staging;
9. DB, Redis, workers y servicios requeridos saludables.

Cualquier check fallido produce `ready=false` y el agente debe detenerse antes de mantenimiento.

## Flujo del Update Agent

```text
CHECK RELEASE
→ VALIDATE MANIFEST
→ VERIFY SIGNATURE + ARTIFACT
→ COMPATIBILITY
→ PREFLIGHT
→ VERIFIED BACKUP
→ MAINTENANCE
→ STAGE NEW RELEASE
→ RUN DB/DATA MIGRATIONS
→ COLLECT STATIC
→ RESTART WEB/WORKERS
→ HEALTH + READ-ONLY SMOKE
→ ONLINE
```

El agente registra cada transición y nunca salta un estado. La activación debe ser atómica o con estrategia blue/green
equivalente; no se considera online hasta que health y smoke pasen.

## Fallos y recuperación

- Antes de mantenimiento: abortar sin modificar la instalación.
- Durante staging: eliminar únicamente el staging del release fallido.
- Tras activar código pero antes/durante migraciones: detener tráfico y no continuar ciegamente.
- Tras una migración fallida: preservar logs, mantener mantenimiento y ejecutar el plan de restore verificado.
- Health/smoke fallido: no marcar éxito; restaurar el conjunto compatible de código, DB y archivos según policy.

No se promete downgrade. El rollback soportado es restore de un backup pre-update verificado, probado primero en un
entorno aislado. El agente debe emitir un estado `failed` accionable y nunca un éxito parcial.
