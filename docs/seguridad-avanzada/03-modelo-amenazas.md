# F3 — modelo de amenazas CIA/STRIDE

Fecha: 2026-10-15

## Método

El modelo sigue las cuatro actividades de OWASP —modelar, identificar, responder y revisar— y usa STRIDE como conjunto de preguntas técnicas. CIA define el impacto. La referencia de proceso es la [OWASP Threat Modeling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html); este documento no constituye una certificación.

Alcance: aplicación Django, navegador, PostgreSQL, Redis, Celery worker/beat, almacenamiento público/privado, correo, mapas, observabilidad, APIs y webhooks. Nginx/TLS, DNS y proveedores reales se tratan como límites externos porque no fueron verificados en infraestructura candidata.

## Activos y objetivos CIA

| Activo | Confidencialidad | Integridad | Disponibilidad |
|---|---|---|---|
| cuentas Staff, credenciales, MFA y sesiones | crítica | crítica | alta |
| clientes, identificadores y solicitudes de privacidad | crítica | alta | media |
| vehículos, ownership, garaje y códigos | alta | alta | alta |
| sucursales e información pública | media | alta | alta |
| pagos, facturas y comprobantes | crítica | crítica | alta |
| inventario, reservas y movimientos | alta | crítica | alta |
| documentos y archivos privados | crítica | alta | media |
| auditoría y alertas | alta | crítica | alta |
| API tokens, firmas e idempotencia | crítica | crítica | alta |
| backups y material de restauración | crítica | crítica | crítica |
| PostgreSQL | crítica | crítica | crítica |
| Redis y mensajes Celery | alta | alta | alta |

## Componentes, flujos y límites de confianza

| Flujo | Origen → destino | Límite | Datos/operación | Controles observados |
|---|---|---|---|---|
| HTTP público | navegador → Nginx/Django | Internet | catálogo, instituciones, leads, registro | Forms, escape, CSRF en mutaciones, rate limit |
| sesión autenticada | navegador → Django/session store | Internet/aplicación | cookie, CSRF, MFA, permisos | Secure en producción, HttpOnly, SameSite, tracking y revocación |
| persistencia | Django → PostgreSQL | aplicación/datos | datos empresariales y personales | ORM, transacciones, constraints, locks |
| colas | Django/beat → Redis → worker | aplicación/cola | identificadores y parámetros de tareas | tareas registradas, límites y reintentos; red real pendiente |
| archivos públicos | Django → media/storage | aplicación/almacenamiento | imágenes autorizadas | extensión, firma real, tamaño e ImageField |
| archivos privados | Django → private/S3 → descarga autorizada | dos límites | documentos, evidencia y backups | storage privado, nombres seguros, URLs firmadas y ownership |
| correo | Django/Celery → proveedor SMTP | proveedor | invitaciones y notificaciones | plantillas, tokens de un uso; contrato/proveedor pendiente |
| mapas | navegador → CDN/MapTiler | tercero | IP y solicitud del navegador | clave pública; consentimiento y restricción de dominio pendientes |
| webhooks salientes | Django/Celery → endpoint tercero | Internet/tercero | evento firmado | HMAC, allowlist de esquemas/IP, idempotencia; DNS rebinding residual |
| webhooks entrantes/API | tercero → API Django | Internet/API | tokens, firma, payload | scopes, rate limit, firma e idempotencia |
| observabilidad | Django → logs/Sentry | proveedor/operación | errores redactados | filtros y redacción; configuración contractual pendiente |
| continuidad | PostgreSQL/storage → archivo/transferencia | datos/operación | dump y manifiestos | hashes, validación, rutas seguras; restore real pendiente |

## Registro STRIDE

| ID | STRIDE / CIA | Escenario | Activo | Control existente y evidencia | Riesgo residual / acción | Prioridad |
|---|---|---|---|---|---|---|
| TM-01 | S / C-I | credencial Staff robada permite suplantación | Staff | lockout, rate limit, política 2FA, sesión rastreada | acceso adaptativo por red/dispositivo todavía ausente; F8 | alta |
| TM-02 | S / C-I | sesión robada se reutiliza | sesiones | HttpOnly/Secure en producción, SameSite, revocación y middleware | revalidar señales de riesgo en sesión; F7–F8 | alta |
| TM-03 | T-E / I | manipular rol, alcance o sucursal | RBAC | `PermissionCode`, asignaciones vigentes, alcance y tests negativos | automatización completa de matriz tras F8 | media |
| TM-04 | E-I / C-I | IDOR entre clientes/sucursales | clientes/documentos | selectors con ownership/branch y pruebas horizontales | conservar pruebas al añadir endpoints | media |
| TM-05 | T / I | alterar pagos, reservas o stock concurrentemente | finanzas/inventario | servicios transaccionales, constraints y `select_for_update` | stress real y observabilidad PostgreSQL pendientes | alta |
| TM-06 | R / I | usuario niega una mutación sensible | auditoría | logs de dominio, actor, before/after, hash encadenado | almacenamiento inmutable externo pendiente | media |
| TM-07 | T-R / I | atacante altera o borra logs | auditoría | acceso restringido, hash chain y alertas | WORM/retención externa no verificados | alta |
| TM-08 | I / C | exportación o listado mezcla sucursales/clientes | datos personales | scopes reutilizados y pruebas de exports | revisión por requisito ASVS y beta humana | media |
| TM-09 | I / C | catálogo público revela costo/stock/reservas | inventario | selector F2 proyecta solo disponibilidad cualitativa | revisión visual y proveedor de imágenes | baja |
| TM-10 | T-I / C-I | upload disfrazado o path traversal | archivos | firma real, tamaño, extensiones, nombres controlados y storage privado | antivirus/CDR ausente; F12 | alta |
| TM-11 | T / I | XSS almacenado/reflejado en textos o URLs | navegador | autoescape Django, validadores URL y DOM sin HTML dinámico en F2 | CSP aún permite inline styles; F5–F6 | alta |
| TM-12 | T / I | SQL/command injection | base/SO | ORM, queries parametrizadas y comandos acotados | Semgrep/Bandit y revisión de subprocess en F6/F11 | media |
| TM-13 | T / I | CSRF ejecuta mutación autenticada | sesión | middleware y tokens CSRF, SameSite adicional | comprobar APIs/HTMX y logout en F7 | media |
| TM-14 | I-E / C-I | SSRF/webhook llega a metadata o red privada | infraestructura | validación de URL y bloqueo de IP privada | resolver/revalidar DNS al conectar; F6 | alta |
| TM-15 | S-T / I | webhook falsificado o repetido | integraciones | HMAC, timestamp/idempotencia | rotación de secretos y prueba con proveedor pendiente | alta |
| TM-16 | D / A | fuerza bruta, formularios o API agotan recursos | web/API | rate limits de login, públicos y clientes API | rate limit distribuido/edge no verificado | alta |
| TM-17 | D / A | archivo grande o bomba de imagen agota memoria | web/worker | límites de bytes/dimensiones y límites Nginx | cuotas por usuario y sandbox AV pendientes | media |
| TM-18 | D / A | tareas Celery se duplican o atascan | colas | idempotencia en flujos críticos, límites/reintentos | DLQ, dashboards y alertas reales pendientes | media |
| TM-19 | I / C | secretos en Git, logs o frontend | secretos | env, redacción, storage privado y escaneo previo | gestor de secretos externo y rotación pendientes | alta |
| TM-20 | T-I / C-I | dependencia comprometida | cadena de suministro | rangos controlados y `pip-audit` B12 | hashes/SBOM/análisis de imágenes pendientes; F11 | alta |
| TM-21 | D-T / A-I | backup corrupto o restauración incompleta | continuidad | manifiestos/hash/verificación local | restore real y RPO/RTO aprobados pendientes | crítica |
| TM-22 | I / C | proveedor de mapa/analítica recibe datos antes de consentimiento | privacidad | no hay analítica propia demostrada | gate de tecnologías opcionales y registro mínimo; F9 | alta |
| TM-23 | E / C-I | cuenta Staff fuera de política conserva APIs privilegiadas | Staff/API | permisos y 2FA | bloqueo/aprobación temporal/revalidación no implementados; F8 | crítica |
| TM-24 | T-D / I-A | autoaprobación o carrera en excepción Staff | Staff | no existe aún ese flujo | diseñar permiso separado, locks, expiración y auditoría; F8 | crítica |
| TM-25 | I-R / C-I | error técnico revela datos o no queda trazado | errores | handlers controlados, redacción y resiliencia del sink | DAST y observabilidad real pendientes | media |

## Respuesta priorizada

1. Diseñar e implementar F8 sin activar restricciones rígidas por defecto.
2. Cerrar SSRF/DNS rebinding, validaciones contextuales y CSP donde sea viable.
3. Inventariar y controlar cookies/scripts externos antes de cargarlos.
4. Añadir SBOM, análisis reproducible y política de actualización.
5. Definir antivirus/CDR o cuarentena según riesgo de cada upload.
6. Ejecutar restore, pruebas de edge/rate limit y observabilidad en staging.

## Relación con SSDF y SAMM

- NIST SSDF 1.1: preparar la organización (PO), proteger software (PS), producir software bien asegurado (PW) y responder a vulnerabilidades (RV). Referencia: [NIST SP 800-218](https://csrc.nist.gov/pubs/sp/800/218/final).
- OWASP SAMM v2: este bloque fortalece Threat Assessment; F4/F5 cubren Security Requirements/Requirements-driven Testing; F11 Secure Build/Defect Management; F12 Operations. Referencia: [modelo SAMM](https://owaspsamm.org/model/).

## Condiciones de revisión

Actualizar este modelo ante nuevos proveedores, autenticación, roles, datos sensibles, APIs, archivos, cambios de red o incidentes. Repetirlo antes de activar la política Staff y antes de producción.
