# VINOVA PRO — Certificación final de integración LITE → PRO

Fecha de cierre técnico: 2026-10-11

Rama: `integration/lite-pro`

Base auditada: `ab39f44` (`test: complete portal integration validation`)

HEAD técnico previo a este informe: `6a11fd8`

## Veredicto

**PREPARACIÓN TÉCNICA PARCIAL — NO PRODUCTION READY.**

La integración ejecutable está estable: no quedan fallos conocidos en las pruebas locales, PostgreSQL, seguridad, continuidad, E2E Chromium ni controles estáticos. Sin embargo, no corresponde certificar producción mientras falten el ciclo real de Cloudinary solicitado, la aprobación visual humana y la comprobación/smoke de una configuración real de despliegue.

No se realizó merge, despliegue, restauración sobre datos reales ni modificación de `web_carros/`.

## Estado por gate

| Gate | Estado | Evidencia principal |
|---|---|---|
| A — PostgreSQL y Docker | **VALIDADO** | PostgreSQL 16 en compose QA aislado; migración desde cero; `migrate --plan` vacío; 8/8 pruebas aprobadas. |
| B — Pruebas omitidas | **VALIDADO** | Suite final: 2.418 passed, 0 failed, 40 skipped, todos clasificados. |
| C — Cloudinary | **PENDIENTE EXTERNO** | Integración local/simulada validada; faltan credenciales y ciclo real de staging. |
| D — Storage privado | **VALIDADO** | Backend activo `local`; lifecycle, autorización, headers, traversal y fallos parciales cubiertos. S3: **NO APLICA** al staging previsto. |
| E — Seguridad y permisos | **VALIDADO** | 1.867 pruebas focales aprobadas y suite final limpia; aislamiento horizontal y controles backend cubiertos. |
| F — Integridad empresarial | **VALIDADO** | 174 pruebas focales aprobadas; módulos empresariales y `post_sales` ON/OFF sin regresiones. |
| G — E2E y visual | **PENDIENTE EXTERNO** | Validación técnica Chromium 32/32 y capturas responsive; falta aprobación visual humana. |
| H — Rendimiento e integridad | **VALIDADO** | 122 pruebas focales aprobadas; query budgets, paginación, idempotencia y compensación de archivos. |
| I — Cierre final | **VALIDADO TÉCNICAMENTE** | Checks, migraciones, Ruff, suite, E2E, backup/restore, release, OpenAPI, JS, paquete y Nginx verificados. |

## Gate A — PostgreSQL, concurrencia y POSIX

Se utilizó el proyecto aislado `vinova-cert-gatea` con `docker-compose.qa-cli.yml`. La base PostgreSQL 16 residió en `tmpfs`; no se accedió a los contenedores ni volúmenes ordinarios del proyecto.

Resultados:

- Migración completa desde una base PostgreSQL limpia: aprobada.
- `python manage.py migrate --plan`: `No planned migration operations`.
- Pruebas focales: **8 passed en 24,39 s**.
- El stack QA fue detenido y eliminado; quedaron **0 contenedores** con el prefijo de certificación.

Las seis carreras PostgreSQL verificadas fueron:

1. Conversión simultánea del mismo lead: una cotización y una conversión.
2. Leads concurrentes con la misma identidad: reutilización del cliente.
3. Numeración concurrente de cotizaciones: números distintos.
4. Canje simultáneo de vehículo: un único propietario activo.
5. Generación concurrente del PDF: un único artefacto.
6. Evento concurrente de cliente: un mensaje y un destinatario.

También se ejecutaron el caso funcional no concurrente del archivo de leads y el control POSIX de permisos de assets compartidos.

## Gate B — Suite y skips

Ejecución final Django en Windows/SQLite de QA:

- **2.418 passed**
- **0 failed**
- **40 skipped**
- Duración: 110,24 s
- JUnit: `run/qa/certification-gate-i-full.xml` (artefacto local ignorado por Git)

Clasificación de los 40 skips:

- 6 dependientes de locks reales de PostgreSQL; todos fueron ejecutados y aprobados por separado en Gate A.
- 32 E2E omitidos deliberadamente por pytest normal; todos fueron ejecutados y aprobados con el runner E2E.
- 1 control POSIX omitido en Windows; fue ejecutado y aprobado dentro del contenedor Linux.
- 1 combinación parametrizada no aplicable: el endpoint de exportación exige un único permiso.

No quedan skips injustificados ni fallos ocultos.

## Gates C y D — Almacenamiento

### Avatar / Cloudinary

- Dependencia instalada: `cloudinary 1.46.3`, compatible con `>=1.44,<2`.
- Selección de backend, validación de contenido/tamaño/formato, persistencia, URL, reemplazo, eliminación, fallback y redacción: validados.
- `.env` y `.env.staging` seleccionan backend local y no aportan las tres credenciales Cloudinary requeridas.
- No se inventaron credenciales ni se usó producción.

Estado: integración **validada localmente**; ciclo real crear/consultar/reemplazar/eliminar **PENDIENTE EXTERNO**.

### Documentos privados, facturas y manuales

- Backend previsto para staging: `PRIVATE_STORAGE_BACKEND=local`.
- Ciclo live aislado del backend local: aprobado.
- Ownership, scoping, transferencias, descargas, `Cache-Control`, `Content-Disposition`, `nosniff`, path traversal y objetos inexistentes: aprobados.
- El adaptador S3 simulado verifica firma temporal, ACL privada, cifrado AES-256, timeouts y redacción. S3 real es **NO APLICA** mientras no sea el backend elegido.
- Los objetos ausentes ahora devuelven respuesta controlada sin registrar descargas falsas (`d844419`).
- Creaciones/reemplazos fallidos limpian el objeto nuevo; los objetos anteriores sólo se eliminan tras commit (`39fd4a1`).

## Gate E — Seguridad

La batería focal obtuvo **1.867 passed, 3 skipped** en su corte y la suite integral posterior terminó sin fallos. Se cubrieron:

- Cliente A, Cliente B, staff, administrador, usuario sin `Customer`, rol vencido y anónimo.
- Aislamiento horizontal, IDs ajenos, vehículos transferidos y datos del propietario anterior.
- Permisos efectivos en backend, no sólo visibilidad de botones.
- CSRF, XSS, validación de entradas, rate limiting, reset de contraseña, sesiones y 2FA.
- Descargas privadas y auditoría de acciones sensibles.

## Gate F — Integridad empresarial

Resultado focal: **174 passed, 4 skipped** en SQLite; las cuatro carreras pendientes de ese corte fueron posteriormente aprobadas en PostgreSQL.

Sin regresiones en clientes, vehículos/VNV, ventas, inventario, facturas/pagos, órdenes de servicio, CRM, notificaciones, sucursales, roles, permisos y configuración modular. `post_sales` se validó tanto habilitado como deshabilitado. No se reintrodujeron SRI, recordatorios automáticos, SaaS ni multitenencia.

## Gate G — E2E y revisión visual

Ejecución Chromium final:

- **32 passed, 0 failed, 0 skipped**.
- 11 grupos de escenarios.
- Duración: 311,532 s.
- Evidencia: `run/qa/certification-gate-i-e2e-final/summary.json` y JUnit local.
- Capturas principales: `portal-desktop.png` y `portal-mobile.png`, además de matrices light/dark y responsive.

El runner cubrió portal, público, autenticación, vehículos, clientes, inventario, ventas/facturación, documentos, seguridad/continuidad, roles y accesibilidad. El portal adicional captura errores de consola, `pageerror` y respuestas HTTP inesperadas (`d2d4bd3`).

La inspección técnica no mostró overflow ni estética gamer/neón y confirmó navegación por teclado, foco, contraste y viewports desktop/tablet/móvil. Esto no sustituye la aprobación visual humana, que permanece pendiente.

## Gate H — Rendimiento e integridad transaccional

Resultado focal final: **122 passed, 2 skipped** antes de validar esas dos carreras en PostgreSQL.

- Presupuesto de consultas del portal: máximo 32.
- Páginas staff: máximo 45 consultas con 30 filas.
- Paginación, índices y restricciones relevantes: presentes.
- Idempotencia de eventos y PDFs: aprobada, incluida concurrencia PostgreSQL.
- Compensación de archivos ante rollback: cubierta por regresiones que simulan fallos de auditoría/base de datos.
- Eliminación posterior al commit para reemplazos de documentos, recursos y avatares.

## Gate I — Cierre técnico

Controles aprobados:

- `manage.py check`.
- `makemigrations --check --dry-run`: sin cambios.
- Migración limpia SQLite y PostgreSQL; planes posteriores vacíos.
- Ruff: limpio.
- OpenAPI v1: válido; se tiparon los campos calculados de inventario (`a99bd39`).
- `pip check`: sin dependencias rotas.
- JavaScript: 3 archivos con sintaxis válida.
- Release estático estricto: 10/10 verificaciones.
- Paquete temporal: 1.295 archivos/entradas, checksum generado y verificado.
- `check --deploy`: limpio bajo controles HTTPS/HSTS productivos explícitos.
- `.env.staging`: consistencia interna aprobada sin imprimir secretos.
- Nginx HTTP/HTTPS: sintaxis válida dentro del contenedor. El verificador fue corregido para renderizar los límites de login (`6a11fd8`).

El `.env` local es deliberadamente de desarrollo y falla `check --deploy` si se usa como producción; este comportamiento fail-closed es correcto. No se lo modificó ni se lo presentó como configuración desplegable.

### Continuidad

Drill aislado sobre runtime nuevo:

- Backup ID: `42210e0e-26fa-4868-8397-84a94d3cf8dc`.
- SHA-256: `90fa661cb3205e4472597d4d38fd81501e2bd11f3dbfe5464a16c8b394e6738f`.
- Verificación de archivo, hash, manifiesto y compatibilidad: aprobada.
- Preparación de restore en directorio vacío: aprobada.
- Componentes extraídos: `database.sqlite3` y `manifest.json`.

No se restauró ni alteró ninguna base real.

## Defectos encontrados y corregidos

| Commit | Corrección | Regresión |
|---|---|---|
| `a2ac223` | Las carreras de leads se declaran PostgreSQL-only en SQLite. | 1 caso funcional aprobado y 3 skips explícitos; luego 4/4 en PostgreSQL. |
| `d844419` | Objetos privados ausentes ya no producen 500 ni auditoría falsa. | Descargas portal/staff y traversal. |
| `d2d4bd3` | E2E portal captura consola, errores de página y HTTP inesperados. | Portal Chromium limpio. |
| `39fd4a1` | Compensación de archivos en rollback/reemplazo de documentos, facturas y avatares. | Fallos simulados y eliminación post-commit. |
| `a99bd39` | Tipos OpenAPI de stock total y stock bajo. | Inventario 7/7 y esquema válido. |
| `6a11fd8` | El validador Nginx sustituye rate/burst de login. | 10 pruebas focales y validación real HTTP/HTTPS. |

## Git, secretos y alcance

- Remoto esperado: `origin` → `https://github.com/Tokyogh/vnv-cncs-.git`.
- Rama autorizada: `integration/lite-pro`.
- `git diff --check`: limpio en los commits de certificación.
- Búsqueda de patrones de claves privadas/tokens en archivos rastreados: sin coincidencias.
- `.env`, `.env.staging`, credenciales privadas y `run/` están ignorados por Git.
- `web_carros/`: sin diferencias desde `ab39f44`.
- Cambios locales ajenos preservados y excluidos de los commits: `AGENTS.md`, matriz/rediseño, reporte R06 y `tmp/`.

## Riesgos residuales y acciones humanas

Antes de autorizar producción se requiere:

1. Proporcionar credenciales Cloudinary de staging y ejecutar el ciclo real temporal, o documentar formalmente que Cloudinary queda fuera del despliegue por usar backend local.
2. Aprobar humanamente las capturas y los flujos visuales.
3. Cargar la configuración real de producción/staging, ejecutar `check --deploy`, preflight de compose y smoke contra el dominio/TLS reales.
4. Confirmar backups externos, retención, monitorización, correo y workers en la infraestructura objetivo.
5. Autorizar por separado cualquier merge o despliegue.

Hasta completar esos puntos, el estado correcto es **NO PRODUCTION READY** aunque la base técnica certificada no presente fallos conocidos.
