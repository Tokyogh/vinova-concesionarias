# B5 — Auditoría de ciberseguridad

Fecha: 2026-10-15

## Alcance y método

Se revisaron las entradas HTTP públicas e internas, formularios, serializadores
DRF, búsquedas, identificadores URL, uploads, importaciones, archivos privados,
webhooks, comandos operativos, configuración de producción, autenticación,
sesiones, 2FA, RBAC, aislamiento de sucursal, auditoría y dependencias Python.

La evidencia combina inspección dirigida, búsquedas de construcciones de alto
riesgo, checks Django, `pip-audit`, pruebas D5, pruebas de seguridad de cada
dominio y Chromium RBAC. No se interpreta la ausencia de un hallazgo como
seguridad absoluta.

## Controles verificados

| Área | Implementación comprobada | Estado |
|---|---|---|
| SQLi | ORM para consultas de usuario; el lock PostgreSQL usa parámetro `%s`; los nombres de DB QA son UUID generados y validados antes del SQL de administración | PROBADO |
| XSS | autoescape de templates, validación contextual y CSP sin `unsafe-inline`/`unsafe-eval` en `script-src`; payload almacenado probado | PROBADO |
| CSRF | middleware Django activo; mutaciones HTML sin token devuelven 403 | PROBADO |
| Autorización/IDOR | PermissionCode, vigencia, scope de sucursal, selectores deny-by-default y ownership de portal/documentos | PROBADO; matriz en `04-matriz-rbac.md` |
| Open redirects | `safe_next_url()` exige host permitido y esquema coherente | PROBADO |
| SSRF | webhook solo HTTP(S), HTTPS fuera de DEBUG, sin credenciales, bloqueo de IP local/privada/reservada y rechazo de redirects | PROBADO con riesgo residual DNS indicado abajo |
| Uploads | allowlist de extensión, tamaño, firmas de contenido, validación Pillow, nombres generados y storage privado | PROBADO |
| Path traversal | rutas resueltas dentro de roots privados; archivos tar rechazan rutas absolutas, `..`, enlaces y duplicados | PROBADO |
| Mass assignment | ModelForms/serializadores enumeran campos; permisos y sucursal se vuelven a validar en servicios/selectores | PROBADO en flujos críticos |
| Autenticación | backend email/usuario, validadores de contraseña, historial, lock/rate limit y reset Django | PROBADO |
| 2FA | TOTP, códigos de respaldo, challenge y reset administrativo con permisos | PROBADO; opt-in por política de forma predeterminada |
| Sesiones | timeout idle, registro/revocación, cambio obligatorio de contraseña y cookies endurecidas en producción | PROBADO |
| Cabeceras | HSTS/HTTPS en producción, CSP, COOP/CORP, nosniff, frame deny, referrer y permissions policy | PROBADO |
| CORS | no se habilita `allow all`; check de despliegue lo prohíbe | CONFIGURADO/PROBADO |
| Rate limiting | login, formularios públicos, DRF y clientes API; 429 verificado | PROBADO |
| Archivos privados | fuera de MEDIA, descarga autenticada/scoped, attachment, no-store y hash | PROBADO |
| Integridad transaccional | `atomic`, `select_for_update`, idempotencia y locks/advisory locks donde corresponde | PROBADO en suites; concurrencia PostgreSQL final en B12 |
| Auditoría/logs | contexto, redacción, hash encadenado y alertas; un fallo del sink se registra sin ocultar la excepción original | PROBADO |
| Secretos | guards de producción, pepper separado, `.env`/private ignorados; escaneo de patrones sin claves privadas/AWS rastreadas | PROBADO sobre archivos versionados |

## Hallazgos corregidos

### SEC-B5-001 — rangos de dependencias vulnerables (alta)

El resolver permitido por `requirements/base.txt` seleccionaba
`djangorestframework 3.16.1` y `cryptography 46.0.7`. `pip-audit` reportó 9
registros de vulnerabilidad (incluidas entradas duplicadas por alias de
advisory) en esos dos paquetes. Los límites impedían instalar las versiones
corregidas.

Corrección:

- `djangorestframework>=3.17.2,<3.18`;
- `cryptography>=50.0.2,<51`.

Evidencia: resolución de 52 dependencias con **0 vulnerabilidades conocidas**;
instalación aislada exacta y 121 pruebas de API, uploads y configuración
aprobadas. El contenedor local existente debe reconstruirse para consumir los
nuevos rangos; no se alteró ni desplegó producción.

### SEC-B5-002 — carga híbrida de settings en pruebas (media)

Dos tests importaban `config.settings.production` después de que Django ya
hubiera cargado `config.settings.test`. Con `.env` deliberadamente ignorado,
esto activaba correctamente el guard de SECRET_KEY, pero generaba dos falsos
fallos y no comprobaba una carga real de producción.

Corrección: el probe carga producción en un intérprete aislado con secretos QA
independientes, no imprime valores y devuelve únicamente flags no sensibles.

### SEC-B5-003 — fallo silencioso del sink de auditoría (media)

Si persistir el evento secundario de un 403 o 500 fallaba, el middleware
conservaba correctamente la excepción original, pero descartaba en silencio el
fallo de observabilidad.

Corrección: conserva el comportamiento fail-safe y emite `logger.exception`
para alertar al operador. Dos regresiones prueban 403 y 500 sin enmascaramiento.

### SEC-B4-001 — autorización directa de cuenta inactiva (alta)

Corregido en B4: las APIs de dominio ahora niegan permisos, alcance y autoridad
a cuentas inactivas, incluido un superusuario desactivado.

## Riesgos residuales y gates

| Riesgo | Severidad | Tratamiento |
|---|---|---|
| No existe lockfile con hashes para Python; los rangos reproducen compatibilidad, no un artefacto inmutable | media | generar/validar lock en el proceso de release antes de producción |
| La validación SSRF resuelve DNS antes de que la librería HTTP vuelva a resolver al conectar; queda una ventana teórica de DNS rebinding | media | usar resolución/conexión fijada a IP con SNI seguro o egress proxy antes de habilitar webhooks no confiables |
| Uploads validan tipo/tamaño/estructura, pero no ejecutan antivirus, CDR ni detección de macros | media | gate de infraestructura/proveedor para archivos de origen no confiable |
| CSP conserva `style-src 'unsafe-inline'` por compatibilidad visual; `script-src` sí está endurecido | baja | migrar estilos inline a clases/nonces en una fase visual controlada |
| Paquetes de transfer/backup no tienen un máximo empresarial configurable de bytes descomprimidos, aunque verifican inventario, hash, espacio y traversal | baja/media | definir capacidad máxima según infraestructura antes de importaciones externas |
| TLS real, proxy, dominios CORS/CSRF, S3/Cloudinary, correo, Sentry y receptores webhook | gate externo | validar en staging; no simulado ni aprobado aquí |
| Política 2FA está deshabilitada por defecto | decisión empresarial | activar en staging/producción para perfiles administrativos tras enrolamiento |

No se aplicaron decisiones empresariales nuevas, sanitización universal ni
relajaciones de permisos. SRI sigue excluido y postventa conserva su feature
flag.

## Evidencia ejecutada

- suite ampliada D5/dominios: **1.872 passed, 1 skipped** en 99,67 s;
- motivo del skip: un caso parametrizado no aplica a un endpoint cuyo contrato
  exige un único permiso;
- regresión de audit sink y módulo audit: **10 passed**;
- dependencias nuevas en venv aislado: **121 passed**;
- `pip check`: sin dependencias rotas en el entorno base;
- `pip-audit -r requirements/production.txt`: **52 dependencias, 0 hallazgos**
  después de la corrección;
- `manage.py check --deploy --settings=config.settings.production`: sin
  incidencias con configuración QA segura y explícita;
- escaneo versionado: sin claves privadas, patrón de access key AWS ni secretos
  de producción literales; solo ejemplos `.env.*.example` y `private/.gitkeep`;
- Ruff focal de archivos modificados: sin incidencias.

## Límites de la conclusión

La aplicación presenta controles de defensa en profundidad comprobados y los
defectos locales encontrados fueron corregidos. No se declara seguridad
absoluta ni readiness de producción: siguen pendientes los gates externos, la
reconstrucción del artefacto con dependencias corregidas, el lock reproducible y
las validaciones finales B12.
