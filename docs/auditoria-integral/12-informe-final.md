# B12 — Informe final de auditoría y consolidación

Fecha de cierre local: 2026-10-15
Rama: `integration/lite-pro`
Base auditada: `50697b3`

## Veredicto

VINOVA PRO queda **apto para avanzar a beta controlada** sobre el commit certificado localmente. No se declara `PRODUCTION READY`: faltan staging con DNS/TLS reales, proveedores externos, restauración sobre infraestructura candidata, revisión legal, aprobación visual y resultados humanos de beta.

## Estado funcional por dominio

| Dominio | Estado demostrado | Observación |
|---|---|---|
| cuentas, roles, 2FA y sesiones | verificado | cuenta inactiva no conserva permisos efectivos; vigencia y revocación probadas |
| empresa y configuración | verificado | monocompañía; no SaaS/multiempresa |
| sucursales e instituciones | verificado | CRUD, coordenadas, publicación, mapa y filtros; foto/website por sede pendientes |
| clientes y portal | verificado | asociación explícita, respuesta sin expediente y ownership horizontal probado |
| vehículos y garaje | verificado | CRUD, publicación, multimedia, catálogo, códigos y canje seguro |
| inventario | verificado | mínimos/ubicación, movimientos, transferencias y locks PostgreSQL |
| CRM, leads y ventas | verificado | captura, pipeline, conversión, cotización, reserva, venta y pagos |
| facturación | verificado | comprobante interno, pagos, anulaciones, PDF y portal; SRI operativo excluido |
| postventa | verificado bajo flag | ON/OFF respetado; recordatorios automáticos excluidos |
| documentos | verificado | storage privado, validación, lifecycle y descargas auditadas |
| notificaciones y campañas | verificado | preferencias, consentimiento, snapshot, confirmación explícita e idempotencia |
| reportes, BI y analítica | verificado | filtros, exportaciones y alcance por sede |
| imports | verificado | plantillas, CSV/XLSX, prevalidación y confirmación; histórico LITE excluido |
| privacidad | verificado localmente | requiere revisión legal antes de producción |
| auditoría | verificado | hash encadenado, redacción, exports, alertas y resiliencia del sink |
| API e integraciones | verificado localmente | scopes, idempotencia, HMAC y controles SSRF; proveedores/TLS pendientes |
| continuidad | verificado localmente | backup, verificación, drill y transfer; restore real pendiente |
| QA y ayuda | verificado | perfiles, evidencia privada, artículos/checklists y ayuda contextual |
| portal público | verificado | inicio, catálogo vehicular, mapa/instituciones y leads; catálogo público de repuestos ausente |

El detalle de 27 apps, 85 modelos y 1.289 patrones URL permanece en [B1](01-inventario-funcional.md).

## Paridad LITE → PRO

- Se contrastaron 68 reglas y recorridos LITE; portal cliente, catálogo vehicular e instituciones conservan la referencia visual/funcional con seguridad PRO.
- PRO mejora RBAC, alcance de sucursal, ownership, transacciones, auditoría, archivos privados, API, continuidad y QA.
- Brechas vigentes: fotografía/website configurables por sede y catálogo público de repuestos equivalente a LITE.
- La reactivación de códigos antiguos se reemplaza justificadamente por emisión nueva y trazable.
- `web_carros/` no fue modificado.

## Roles y autorización

- 13 roles oficiales × 63 permisos inventariados y contrastados.
- Se probaron permitidos/denegados, cuenta inactiva, rol futuro/expirado/revocado, módulo OFF, URL directa, CSRF, recurso ajeno, sucursal ajena y cliente sin expediente.
- Los seis roles de sucursal obligatoria conservan ese límite; los roles globales no se reinterpretaron.
- La suite beta incluye una guía por rol y negativos de branch/ownership.

## Ciberseguridad

Correcciones confirmadas:

- cuentas inactivas se deniegan también en helpers/servicios de dominio;
- fallos del sink de auditoría se registran sin ocultar la denegación/error original;
- DRF y `cryptography` se actualizaron a rangos sin advisories conocidos;
- settings productivos se prueban en intérprete aislado;
- regresión de encoding evita texto corrupto visible.

Riesgos residuales:

- dependencias Python sin lock con hashes;
- defensa adicional contra DNS rebinding en webhooks no confiables;
- ausencia de antivirus/CDR para uploads externos;
- `style-src 'unsafe-inline'` aún permitido;
- límites operativos de archivos/archivos de continuidad por validar en infraestructura real;
- controles y contratos no equivalen a seguridad absoluta.

## Limpieza y documentación

- Se eliminaron 15 artefactos confirmados: scripts puntuales, logs, muestra PDF/PNG y Nginx heredado sin consumidor.
- Se conservaron migraciones, fixtures, seeds, históricos, baseline visual, `nd.txt`, privados y el cambio ajeno de `.gitignore`.
- README y documentación canónica cubren arquitectura, funciones, datos, RBAC, seguridad, APIs, despliegue, operación, testing, paridad y estado.
- 556 módulos Python, 201 templates, 50 CSS, 5 JS propios y 12 configuraciones Docker/Nginx tienen encabezados de responsabilidad.
- `docs/testeo-beta/` contiene 30 documentos y 214 casos manuales inicialmente `pendiente`.

## Resultados finales

| Validación | Resultado |
|---|---|
| Django check + drift | 0 incidencias; 0 migraciones sin generar |
| migraciones locales | `notifications.0005` aplicada; base local al día |
| Ruff, compileall, JavaScript, pip check | aprobados |
| suite completa | 2.470 aprobadas, 41 omitidas, 0 fallos |
| skips clasificados | 33 E2E y 7 PostgreSQL aprobados separadamente; 1 parametrización negativa intencional |
| RBAC/ownership/seguridad focal | 886 aprobadas, 1 omitida intencional |
| concurrencia PostgreSQL | 7 aprobadas |
| E2E Chromium | 33 aprobadas, 0 omitidas/fallidas; 11 escenarios |
| release readiness | 11/11 checks estáticos/runtime, DB y Celery |
| producción aislada | `check --deploy` y probe de cookies/settings aprobados con valores QA |
| dependencias de release | `pip-audit -r requirements/production.txt`: 0 vulnerabilidades conocidas |
| Nginx | plantillas HTTP/HTTPS válidas con Nginx 1.30 |
| paquete release | 1.355 archivos/entradas y SHA-256 generado en temporal |
| documentación | 124 Markdown, 0 enlaces locales rotos |
| secretos fuertes | 0 archivos coincidentes en contenido versionado |
| diff | `diff --check` limpio; 0 cambios en `web_carros/` |

La primera pasada completa reveló una expectativa antigua: el test de registro concedía `portal.access` antes de activar la cuenta. Se corrigió el test para exigir denegación mientras `is_active=False` y permiso sólo después de la activación; la repetición total quedó verde.

## Gates externos y bloqueos

- staging candidato con DNS, TLS, cabeceras y smoke post-despliegue;
- ciclos reales Cloudinary/MapTiler/correo/Sentry/webhooks/S3 cuando apliquen;
- restricciones de dominio para claves públicas;
- restore real con backup verificado y rollback ensayado;
- revisión legal de privacidad/retención;
- aprobación visual LITE→PRO y ejecución humana de las guías beta.

Ningún gate se marcó aprobado sin ejecutarlo.

## Commits

La serie autónoma parte de `50697b3` e incluye B0–B11 en commits independientes. El cierre B12 incorpora la corrección de expectativa, higiene final del diff, este informe y el checkpoint. Véase `git log 50697b3..integration/lite-pro` para hashes completos.
