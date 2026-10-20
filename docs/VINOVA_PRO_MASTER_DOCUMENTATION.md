# VINOVA PRO — Master Documentation

> Documento maestro de auditoría integral. Estado: **actualizado en D9** — todo el contenido refleja
> el producto verificado por las fases D0–D8 (código, tests, E2E, PostgreSQL real, Redis y Chromium).
> Este documento **no equivale a aprobación visual humana** y se actualizó contra el código real,
> no contra documentación histórica.
>
> Última actualización: 2026-10-07 · Commit de referencia: `ea50bfa` (D8) · Rama: `feature/v0-2-auth-roles`
>
> Convención de estados usada en todo el documento:
> `VERIFICADO` (comprobado por código/test/E2E/runtime) · `NO VERIFICADO` (no pudo comprobarse)
> · `PENDIENTE` (falta ejecutarlo) · `NO APLICA` (no corresponde al producto real).

---

## 1. Identidad y alcance

- **Producto:** VINOVA PRO, versión `2.0.0` (`config/settings/base.py`, `README`). **VERIFICADO**.
- **Propósito:** plataforma de gestión automotriz multiusuario y multisucursal para **una organización**.
- **Modelo:** **single-tenant NO SAAS**. **VERIFICADO**: no existe `tenant_id`; `Company` es el contexto
  de la organización/empresa (una instalación = una organización), no un mecanismo de tenancy.
  El aislamiento funcional se basa en sucursal, usuario, rol, permisos, ownership y alcance.
- **Filosofía:** “VINOVA se adapta a la organización” — módulos configurables, flags con comportamiento real
  (backend protege lo que la UI oculta). **VERIFICADO** para postventa.
- **Postventa:** módulo opcional `VINOVA_MODULE_POST_SALES_ENABLED` (default `False`). **VERIFICADO**:
  OFF ⇒ navegación sin entradas, listados/URLs directas y mutaciones devuelven `404`, tareas/notificaciones
  no generan órdenes. ON ⇒ funcionalidad autorizada activa (`post_sales.view/manage`).
- **3D:** opcional (`static/js/model_viewer.js`); no es dependencia del núcleo. **PENDIENTE** de prueba
  específica de que no descarga recursos con OFF.
- **SRI:** integración opcional desacoplada (`sri_integration`), settings `sri.manage`; no es dependencia del núcleo.
- **WhatsApp/chat interno:** no existe chat integrado; sí notificaciones/campañas (`notifications`, `campaigns.*`).

---

## 2. Arquitectura y stack (VERIFICADO en runtime D8)

| Área | Implementación real | Estados |
|---|---|---|
| Backend | Python 3.12.10, Django 5.2.16, Django REST Framework, django-filter, drf-spectacular | **VERIFICADO** (D8) |
| Base de datos | PostgreSQL 16 (default `DATABASE_URL`); SQLite solo si no se configura; settings de test aísla | **VERIFICADO** (D8 con PG real aislado) |
| Caché / colas | Redis (caché + broker/result) y Celery (`default,backups,webhooks`; worker `qa` en perfil QA) | **VERIFICADO** configuración y Redis runtime (D8); entrega de tareas celery **NO VERIFICADO** |
| Servidor/proxy | WSGI/ASGI; Gunicorn en `docker-compose.prod.yml`; Nginx proxy frontal; redes internas `backend` | Configuración **VERIFICADO** estático; despliegue vivo **NO VERIFICADO** |
| Frontend | Templates Django + HTMX (`static/vendor/htmx/htmx.min.js`) + JavaScript propio (CSS modular `core/components/layouts/pages/responsive/accessibility`; `theme.js` para Light/Dark) | **VERIFICADO** (D5–D8: E2E + visual) |
| Almacenamiento | `media/` público no servido en producción; raíz privada configurable (`PRIVATE_STORAGE_ROOT`); MinIO opcional en Compose dev | **VERIFICADO** (no se sirve media; acceso privado por permiso) |
| Idioma/zona horaria | `es-ec`, `America/Guayaquil`, `USE_TZ=True` | **VERIFICADO** (config) |
| QA automatizado | Runner `apps/quality/runner.py` + perfiles `quick|full|release` + Celery scheduled QA | **VERIFICADO** (D4/D8 full PASS) |

---

## 3. Estructura del proyecto

Aplicación modular: **26 apps** de producto en `apps/` — `accounts`, `analytics`, `api`, `audit`,
`branches`, `common`, `companies`, `continuity`, `customers`, `dashboard`, `documents`, `enterprise`,
`help_center`, `imports`, `inventory`, `invoices`, `leads`, `notifications`, `post_sales`, `privacy`,
`quality`, `reports`, `sales`, `security_center`, `sri_integration`, `vehicles`.

Inventario estático (VERIFICADO): 45 migraciones numeradas, 27 archivos `urls.py`, 46 `views.py`, 25 `services.py`,
23 `forms.py`, 6 `tasks.py`, 44 comandos de gestión. Modelos por dominio:

| App | Clases de modelo |
|---|---|
| accounts | `PermissionCode`, `Role`, `User`, `UserRole` |
| analytics | `VehicleInteraction` |
| api | `APIScope`, `APIClient`, `IdempotencyRecord`, `IntegrationLog`, `WebhookEndpoint`, `WebhookEvent`, `WebhookDelivery` |
| audit | `AuditLog`, `SecurityAlert` |
| branches | `Branch` |
| common | `TimeStampedModel`, `SoftDeleteModel` (base) |
| companies | `Company` |
| continuity | `BackupPolicy`, `BackupRecord`, `RestoreDrill` |
| customers | `Customer`, `CustomerVehicleInterest`, `CustomerNote` |
| dashboard | — (sin modelos) |
| documents | `DocumentCategory`, `ReusableAsset`, `PrivateDocument` |
| enterprise | `CompanyPublicSettings`, `ApprovalPolicy` |
| help_center | `HelpCategory`, `HelpArticle`, `HelpChecklist`, `HelpChecklistItem`, `UserChecklistProgress`, `UserHelpPreference` |
| imports | `ImportBatch`, `ImportRow` |
| inventory | `InventoryCategory`, `InventoryItem`, `BranchStock`, `StockMovement` |
| invoices | `InvoiceSequence`, `InvoiceRecord`, `InvoiceLine`, `InvoicePaymentApplication`, `InvoiceStatusHistory` |
| leads | `Lead`, `LeadActivity`, `TestDrive` |
| notifications | `NotificationTemplate`, `NotificationMessage`, `NotificationRecipient`, `Campaign`, `CampaignRecipient` |
| post_sales | `ServiceOrder`, `ServiceOrderLine`, `ServiceOrderHistory` |
| privacy | `ConsentRecord`, `DataSubjectRequest`, `DataExportJob`, `RetentionPolicy`, `AnonymizationRecord` |
| quality | `QualityRun`, `QualityCheckResult` |
| reports | `ReportExportJob` |
| sales | `SaleRecord`, `SaleLine`, `SalePayment`, `SaleStatusHistory` |
| security_center | `SecurityPolicy`, `UserSecurityProfile`, `PasswordHistory`, `ActiveSession` |
| sri_integration | `SriConfiguration`, `SriEstablishment`, `SriSequence` |
| vehicles | `VehicleBrand`, `VehicleModel`, `VehicleResource`, `Vehicle`, `VehicleMedia`, `VehiclePartSpecification`, `VehicleCommercialHighlight` |

---

## 4. Configuración, instalación y deployment

- Settings: `config.settings.base`, `local`, `production`, `test`. **VERIFICADO**.
- `test` aísla medios/privados/estáticos a directorio temporal, caché local y tareas eager; usa SQLite
  salvo `TEST_DATABASE_URL`. **VERIFICADO** — por eso las pruebas de concurrencia requieren PG real.
- Instalación local: copiar `.env.example` → `.env`, Docker Compose, migrar, `seed_roles`,
  `seed_api_scopes`, `seed_help_center`, crear superusuario. **VERIFICADO** operativo en entorno local/D8
  con comandos de seeds idempotentes (`check_seed_idempotency` en perfil `release`).
- Compose: `web`, `db` (PostgreSQL 16), `redis` (7), `mailpit`, `celery_worker`, `celery_beat`; perfil
  opcional `object-storage` (MinIO) solo en desarrollo. `docker-compose.prod.yml`: red `backend` interna,
  Gunicorn, `app_init` ejecuta `check --deploy`, migraciones, `collectstatic` y normalización de assets;
  solo Nginx publica puertos. **VERIFICADO** (config estática); despliegue vivo **NO VERIFICADO**.
- Producción (`config.settings.production`): redirect HTTPS por defecto, cookies seguras (session/CSRF),
  HSTS configurable, sesión de 8 h, bloqueos de arranque por `SECRET_KEY` insegura, pepper inválido/compartido
  con `SECRET_KEY`, o webhooks a redes privadas. **VERIFICADO** (config); `check --deploy` se ejecuta en el
  perfil `release` (NO ejecutado en D8; solo `release.readiness` estático y `django.check`).

---

## 5. Base de datos y modelo

- Usuario personalizado `accounts.User` (`AbstractUser`, email único, sucursal opcional, alerta de cambio de
  contraseña, conteo de intentos y bloqueo). **VERIFICADO**.
- Migraciones: **45 numeradas**. `makemigrations --check --dry-run` sin cambios en D4/D8. **VERIFICADO**.
- Aplicación real contra PostgreSQL aislado: `migrate --noinput` en perfil `release`
  (NO ejecutado en D8; D8 usó DB creada + tests con `--create-db`). **PENDIENTE** el paso `database.migrate`.
- Integridad/ownership por dominio cubiertos por suites (branch scopes, IDOR, import scopes). **VERIFICADO** (D2/D5/D7).

---

## 6. Autenticación, autorización y scopes

### Autenticación
- `EmailOrUsernameBackend`; logout/login en `accounts`; validadores Django + `VinovaPasswordPolicyValidator`
  (historial, pepper). **VERIFICADO**.
- Seguridad: contador de 5 intentos y bloqueo 15 min (`VINOVA_LOGIN_MAX_ATTEMPTS/LOCK_MINUTES`); cookie
  sesión HttpOnly SameSite=Lax; CSRF cookie SameSite=Lax; expiración de sesión 8 h en producción. **VERIFICADO**.
- Rate limiting: login con limiter; formularios públicos 8/horas por ventana (`VINOVA_PUBLIC_FORM_*`);
  API 60/h anónimas, 1200/h usuario, 600/h cliente API. **VERIFICADO** (D5 tests de throttling).

### Autorización
- `accounts.User` expone roles activos (`active_roles`), códigos de permiso y panel; `UserRole` tiene
  estado, vigencia (`starts_at`/`expires_at`) y sucursal. **VERIFICADO**.
- `accessible_branch_ids()`: `()` sin acceso, `None` si alcance global, tupla de sucursales si restringido. **VERIFICADO**.
- **Deny-by-default efectivo en backend**: URL directa, POST/PATCH/DELETE, exports, descargas, APIs
  revalidan permisos/scope; no basta ocultar botones. **VERIFICADO** (D2, D5, D7).

### Rol · Permisos sembrados (VERIFICADO estático y de comportamiento)
`seed_roles` crea **13 roles**: `superadmin`, `admin_general`, `admin_sucursal`, `gerente_comercial`,
`jefe_inventario`, `vendedor`, `asesor_postventa`, `facturacion`, `bodega`, `marketing`, `soporte_cliente`,
`auditor`, `cliente`.

Catálogo de permisos: `dashboard.view`; `accounts.manage_users`, `accounts.assign_roles`;
`companies.manage`; `branches.manage`; `vehicles.view/manage/publish/delete_permanent`; `inventory.view/manage_stock`;
`customers.view/manage`; `sales.quote/reserve/sell`; `invoices.view/issue/manage/void`; `documents.view/manage/download_private`;
`notifications.view/send/manage_templates`; `reports.view`; `imports.manage`; `data.export`; `enterprise.manage`;
`sri.manage`; `approvals.manage`; `audit.view/export/manage_alerts`; `campaigns.view/manage/send`; `leads.view/manage/assign/export`;
`analytics.view/export`; `continuity.view/manage/restore`; `privacy.view/manage/export/anonymize`;
`security.view/manage`; `integrations.view/manage`; `help.view/manage`; `quality.view/run`; `post_sales.view/manage`.

Permisos por rol (mapa del seed; `+ help.view` para todo rol excepto `cliente`):

| Rol | Permisos sembrados |
|---|---|
| superadmin | Catálogo completo (todas las rutas globales) |
| admin_general | Catálogo completo (todas las rutas globales) |
| admin_sucursal | dashboard, vehicles.view/manage, inventory.view/manage_stock, customers.view/manage, sales.quote/reserve/sell, invoices.view/issue, documents.view/manage/download_private, notifications.view/send/manage_templates, campaigns.view/manage/send, reports.view, imports.manage, data.export, leads.view/manage/assign/export, analytics.view/export, privacy.view/manage/export |
| gerente_comercial | dashboard, vehicles.view, customers.view, sales.quote/reserve/sell, invoices.view, documents.view/download_private, notifications.view/send, campaigns.view/manage/send, reports.view, leads.view/manage/assign/export, analytics.view/export |
| jefe_inventario | dashboard, vehicles.view/manage, inventory.view/manage_stock, reports.view, imports.manage, data.export |
| vendedor | dashboard, vehicles.view, customers.view/manage, sales.quote/reserve, documents.view, notifications.view/send, leads.view/manage |
| asesor_postventa | dashboard, customers.view, documents.view/download_private, notifications.view/send, post_sales.view/manage |
| facturacion | dashboard, sales.sell, invoices.view/issue/manage/void, documents.view/manage/download_private, notifications.view/send |
| bodega | dashboard, inventory.view/manage_stock |
| marketing | dashboard, vehicles.view/manage/publish, customers.view, notifications.view/send/manage_templates, campaigns.view/manage/send, imports.manage, analytics.view |
| soporte_cliente | dashboard, customers.view, documents.view, notifications.view/send, leads.view/manage, privacy.view/manage |
| auditor | dashboard, vehicles.view, inventory.view, customers.view, sales.quote, invoices.view, documents.view, notifications.view, reports.view, data.export, audit.view/export, leads.view/export, analytics.view/export, continuity.view, privacy.view/export, security.view, integrations.view, quality.view |
| cliente | Ninguno (portal público/perfil) |

Estados de verificación de la matriz:
- **VERIFICADO (estático)** — mapa del seed declarado en `seed_roles`.
- **VERIFICADO (comportamiento)** — 81 casos de roles/scope/API PASS (D2); recorrido Playwright de
  13 roles × 23 rutas PASS (D3) con IDOR de sucursal de vehículos denegado y flag Postventa OFF `404` (D3/D5);
  action sweep 20/20 con denials reales (D7); auditoría visual 302 checkpoints con 0 fallos (D6/D8).
- 3 casos con `tmp_path` quedan bloqueados en runners Windows (limitación del runner, no del producto): **PENDIENTE** de runner con temporales permitidos.

---

## 7. Rutas, APIs y módulos opcionales

- `config/urls.py`: salud, admin Django, `/dashboard/…` (interno staff), `/accounts/…`, `/security/…`,
  empresas/sucursales, vehículos/leads/privacidad públicas, OpenAPI/Swagger, `/api/`, `/api/v1/`. **VERIFICADO**.
- API REST: `IsAuthenticated` por defecto + `APIClientAuthentication` (bearer con pepper) + sesión; scopes de
  API, filtro de sucursal, throttling e idempotencia (TTL 24 h). **VERIFICADO**.
- Hallazgos de API documentados en §11.
- **Feature flags con comportamiento real (VERIFICADO):**
  - `VINOVA_MODULE_POST_SALES_ENABLED` (default `False`): mixin `OptionalModuleRequiredMixin` en vistas,
    guardas en servicios, navegación, notificaciones y tasks; OFF ⇒ 404 en GET y POST directas.
  - `VINOVA_AUTOMATED_BACKUPS_ENABLED` (default `False`): backups programados off.
  - `VINOVA_QA_EXECUTION_ENABLED` / `VINOVA_QA_AUTOMATED_ENABLED` (default `False`): controlan ejecución QA
    automática/por API (Celery).
  - `VINOVA_API_DOCS_PUBLIC` (default `True` en base/local; `False` en producción): ver hallazgo §11.
- Otros flags relevantes (VERIFICADOS): `VINOVA_MAX_UPLOAD_MB=25`, `VINOVA_WEBHOOK_ALLOW_PRIVATE_NETWORKS=False`,
  `VINOVA_REQUIRE_CELERY_READY=False`, `VINOVA_TRUST_PROXY_HEADERS=False`, `VINOVA_QA_MAX_CONCURRENT_RUNS=1`,
  `VINOVA_QA_REPORT_ROOT=<privado>/qa_reports`, retención QA 90 días, `VINOVA_IDEMPOTENCY_TTL_HOURS=24`.

---

## 8. Backend, Celery, archivos y exports

- **Celery**: colas `default,backups,webhooks` (+ `qa`); beat agenda expiración de ventas, heartbeat,
  backups, QA diario y retención de evidencia. Config **VERIFICADO**; ejecución real de workers **NO VERIFICADO**
  (D8 no desplegó beat/worker; Redis runtime sí verificado).
- **Uploads**: validación compartida de extensión/tamaño (25 MB) y almacenamiento privado; pruebas de
  documentos/vehículos (MIME/content), acceso privado por permiso. **VERIFICADO** (D5).
- **Exports**: exporters/datasets en `apps/api/datasets.py`; cada export revalida permiso + alcance de
  sucursal (incluso vía `?output=csv`). **VERIFICADO** (D5: export authorization + información expuesta).
- **Notificaciones**: plantillas, mensajes, destinatarios y campañas; trigger de tareas y feature flag ON/OFF. **VERIFICADO** (tests + action sweep).

---

## 9. Seguridad (auditoría defensiva D5, VERIFICADO)

Cobertura confirmada por `tests/security` (1642 PASS + 1 SKIP en D5; 9 suites re-ejecutadas VERDE en D8):

- **Autenticación/sesiones:** login/logout, bloqueo por intentos, endpoints anónimos (barrido de 756 rutas
  sin 5xx tras fix), cookies (HttpOnly, SameSite, Secure en prod). 
- **Autorización:** matriz por rol, escalación vertical/horizontal, acceso sin rol, exports, descargas.
- **IDOR:** lectura y mutación por sucursal/propietario (fix f11ea1b en imports y documentos).
- **CSRF:** 12 endpoints mutativos revalidan token; API idempotente.
- **XSS:** sin `|safe`/`mark_safe`/`autoescape`/`innerHTML` inyectado; plantillas seguras. 
- **SQLi:** consultas parametrizadas (revisión + tests).
- **Uploads:** extensión/MIME/renombrado/falsificados/descarga; sin ejecución.
- **CSP/headers:** nosniff, referrer-policy, frame DENY, headers propios; sin secretos en health (health sin
  datos sensibles) y media no servida en producción. 
- **Rate limiting:** login y formularios públicos; API throttling.
- **Información expuesta:** 404/500 sin traceback (redondeado con plantillas propias D7 — ver §11).

---

## 10. Frontend y UI/UX (VERIFICADO por E2E + visual)

- **Dashboard adaptativo VINOVA NEXT (N03): IMPLEMENTADO/VERIFICADO.** Un solo shell y un registro declarativo
  resuelven perfil, widgets y Quick Actions con permisos reales; los selectores canónicos aplican alcance de
  sucursal/ownership antes de agregar o listar datos. Las preferencias de orden viven en sesión y se filtran
  nuevamente contra el registro autorizado, por lo que no pueden reactivar contenido al perder permisos.
  Las rutas históricas por área se conservan por compatibilidad, pero renderizan la misma arquitectura compartida.
- **Dashboard Visual 2.1 (N04): TECHNICAL UI PASS.** Composición espaciosa con banner bajo, KPI prioritarios,
  actividad, tareas, Quick Actions y estados secundarios; responsive verificado en 1440x900, 1366x768,
  1024x768, 768x1024 y 390x844, en Light/Dark, sin overflow ni errores de consola. Evidencia Chromium en
  `private/qa_reports/vinova-next/n04/`. Esto no implica aprobación visual humana (`VISUAL_APPROVED: NO`).
- **Filtros 2.0 (N05): IMPLEMENTADO/VERIFICADO.** Un panel reutilizable combina búsqueda, filtros comunes,
  orden mediante allowlists, filtros avanzados, chips removibles, limpieza total y paginación que conserva la
  URL. Está integrado en vehículos, clientes, ventas, inventario, facturas, leads y documentos. Las vistas
  guardadas persisten localmente por usuario y listado únicamente la URL; al abrirlas, cada endpoint vuelve a
  aplicar permisos y alcance en backend. Chromium verificó Light/Dark en 1366x768 y 390x844 sin overflow ni
  errores de consola; evidencia en `private/qa_reports/vinova-next/n05/`.
- **Navegación inteligente (N06): IMPLEMENTADA/VERIFICADA.** El registro único filtra destinos por permisos y
  módulos antes de producir sidebar, breadcrumbs y dataset de Ctrl+K, sin consultas SQL. Favoritos y recientes
  se guardan por usuario en el navegador y se intersectan siempre con los destinos autorizados actuales. La
  paleta soporta búsqueda por metadata, flechas, Enter, Escape, foco confinado y cierre explícito; responsive
  Light/Dark validado en Chromium. Evidencia en `private/qa_reports/vinova-next/n06/`.
- **VINOVA Assist V1 (N07): IMPLEMENTADO/VERIFICADO.** Asistente determinista integrado en Ctrl+K, respaldado
  por un registry de intents y metadata real. Resuelve consultas naturales, ayuda contextual, destinos, acciones
  no destructivas y filtros estáticos seguros; el endpoint autoriza antes de devolver cada deep-link y carga los
  permisos vigentes en una sola consulta para usuarios con rol. No usa LLM externo ni accede a datos comerciales.
  Los intentos restringidos informan falta de acceso sin revelar la ruta. Evidencia responsive Light/Dark en
  `private/qa_reports/vinova-next/n07/`.
- **Búsqueda universal (N08): IMPLEMENTADA/VERIFICADA.** Ctrl+K consulta vehículos, clientes, leads, ventas,
  facturas y documentos reales. Cada fuente se autoriza antes de construir su queryset y reutiliza el selector
  canónico del módulo para aplicar sucursal y ownership en backend; los resultados se limitan por fuente y enlazan
  únicamente a detalles reales. Las preferencias o el frontend no intervienen en la autorización. La regresión
  dirigida cubre ausencia de permisos, aislamiento entre sucursales y presupuesto acotado de consultas; Chromium
  validó teclado y responsive Light/Dark. Evidencia en `private/qa_reports/vinova-next/n08/`.
- **Public/Auth polish (N10): TECHNICAL UI PASS.** Home, catálogo, detalle de vehículo, servicios, About,
  contacto y Login conservan una jerarquía corporativa común, controles accesibles y recomposición móvil. La matriz
  Chromium verificó cinco rutas en 1440x900, 1366x768, 1024x768, 768x1024 y 390x844, Light/Dark: 50 combinaciones
  sin overflow, controles sin nombre, imágenes rotas ni errores de consola. Se corrigió además el landmark `main`
  duplicado del dashboard. Evidencia en `private/qa_reports/vinova-next/n10/`. Esto no implica aprobación visual
  humana y los assets fotográficos definitivos de N09 continúan pendientes.
- **Lifecycle foundation (N11): IMPLEMENTADA/VERIFICADA.** La versión del producto, el ledger/fingerprint de
  migraciones, el formato de backup y el formato de transfer son identificadores independientes y consultables con
  `show_vinova_lifecycle`. El contrato sólo permite upgrades forward cuando el release declara compatibilidad y existe
  una ruta de migración; exige preflight/backup verificado y no presenta downgrade como seguro. La política completa
  de rollback por restore validado está en `docs/LIFECYCLE.md`.
- **Backup/Transfer (N12): IMPLEMENTADO/VERIFICADO.** El backup v3 añade ledger de migraciones e inventario con
  tamaño/SHA-256 por archivo, valida miembros TAR y conserva lectura del formato v2. Restore distingue integridad de
  compatibilidad y sólo prepara extracción aislada. El formato `.vinova` exporta una fixture lógica y media/private
  portable, desactiva/redacta credenciales, MFA, sesiones y secretos, y exige reprovisionamiento. Validación e import
  staging fallan ante traversal, manipulación, formato/versión incompatibles, falta de espacio o destino no vacío.
  Contratos operativos en `docs/BACKUPS.md` y `docs/TRANSFER.md`.
- **Update architecture (N13): IMPLEMENTADA/VERIFICADA.** Release manifest canónico firmado con Ed25519, `key_id`
  confiable externo, artefacto verificado por tamaño/SHA-256 y preflight fail-closed de compatibilidad, migraciones,
  backup, PostgreSQL, espacio y dependencias. El preflight Django es read-only y no despliega. El Update Agent vive
  fuera del request processing; `web` conserva filesystem read-only, capabilities eliminadas y ningún Docker socket.
  Flujo y recovery en `docs/UPDATE_ARCHITECTURE.md`.
- **Update Center (N14): IMPLEMENTADO/VERIFICADO.** La vista administrativa autorizada muestra versión, migration
  state, último backup verificado y health reales. Sólo expone release/preflight y estado del agente cuando existen
  fuentes externas configuradas y saneadas; falla cerrada sin filtrar rutas y no ofrece acciones web de despliegue.
  Chromium validó Light/Dark, teclado y ausencia de overflow; no implica aprobación visual humana.
- **QA VINOVA NEXT (N15): VERIFICADO.** El perfil `full` final pasó 9/9 gates sin advertencias sobre PostgreSQL y
  Redis aislados: Ruff, Django check, drift de migraciones, readiness, smoke, OpenAPI, dependencias, 2181 pruebas
  pytest y 29 recorridos Chromium. Los 30 skips declarados corresponden a condiciones explícitas de suite; no hubo
  regresiones CRITICAL/HIGH/MEDIUM. Evidencia privada: run `18332f06af4146d3b76210c12df00c55`.

- Templates modulares por dominio, componentes reutilizables; base pública y shell staff con sidebar,
  drawer móvil, topbar, tema Light/Dark `data-theme` (theme.js), navegación por permisos y **guardas en
  backend independientes de la UI**.
- **Responsive:** sin overflow horizontal en 320–1920 px de ancho; drawer y navegación móvil recompuestos
  (test_10/11/12 E2E + visual audit en 1440x900, 768x1024, 390x844). **VERIFICADO** (D4/D6/D8).
- **Light/Dark:** 13 roles × rutas × 3 viewports con `data-theme` correcto; estados con ambas temas;
  página 403 propia ya aplica tema (fix D7). **VERIFICADO** (D6/D8).
- **Estados UI:** formulario con errores, tabla vacía, sin resultados, modal de ficha, catálogo vacío,
  403 denegado, loading/success (visual states 0 fallos). **VERIFICADO** (D6/D8).
- **Accesibilidad:** controles etiquetados, focus visible, keyboard en drawer, liga de saltos. **VERIFICADO** (D4/D8).
- **Aprobación visual humana:** **PENDIENTE / NO VERIFICADO** (no se afirma `VISUAL APPROVED`).

---

## 11. Problemas, hallazgos y deuda

### Corregidos (con regresión)

| ID | Severidad | Hallazgo | Fix | Regresión |
|---|---|---|---|---|
| D5-1 | HIGH | Branch-IDOR en importaciones (lectura + mutación) y scope de documentos ignoraba vigencia | `f11ea1b` (apps/imports/{selectors,views,forms}.py, api/views.py, apps/documents/selectors.py) | Suite D5 VERDE |
| D5-2 | HIGH | 14 vistas devolvían 500 a anónimos (permisos antes de sesión) | `16a9316` (analytics, audit, leads, api/internal, 9 dashboards) | Sweep 756 rutas anónimas sin 5xx |
| D5-3 | MEDIUM | Por defecto, acciones sensibles sin deny-by-default (exports, CSRF, exposición) | `ce9bd84` (suites defensivas) | Suite D5 VERDE |
| D6-1 | MEDIUM | Plantillas de error Django por defecto (403/404/500) sin branding ni tema, con códigos numéricos en body | `c6df1e5` (D7): `templates/components/error_document.html`, 403/404/500, `errors.css`, theme.js, sin números/traceback | D7 error-templates 4 PASS + D5 info-exposure + visual D8 (403 con data-theme, notes 0) |
| D7-1 | LOW | N+1 en consultas de vehículos (31 consultas modelo→brand) | `c6df1e5`: `select_related("model__brand"/"vehicle__model__brand")` en 11 archivos | Performance budget PASS |
| D7-2 | LOW | Sobrecarga de queries en dashboards (reports 61q, admin 54q sobre budget 45) | `c6df1e5`: `_evolution_series` (TruncMonth) en executive_summary_context (14→6q) y agregaciones admin | reports 36q, admin 48q aisladas |
| D3/D2 | INFO | 4 expectativas de test obsoletas (CSS modular / tip contextual) | Expectativas actualizadas sin cambio de producto | 4/4 PASS |

### Abiertos (documentados, sin corrección de código; ver decisión al final)

| ID | Severidad | Hallazgo | Razón |
|---|---|---|---|
| D5-4 | INFO | `/api/`, `/api/v1/`, `/api/v1/meta/` responden 200 a usuarios autenticados (enumeración de rutas; sin datos). `meta/` es el health-check oficial de clientes API cubierto por tests | No es fuga de datos ni mutación; riesgo bajo |
| D5-5 | LOW | `/security/2fa/challenge/` accesible con sesión sin flujo 2FA previo (no permite avanzar sin secreto válido) | Sin primitiva de explotación; se mantiene |
| D5-6 | INFO | `VINOVA_API_DOCS_PUBLIC` default `True` en base/local; `production.py` lo fuerza a `False` | Riesgo solo si se despliega sin `production.py`; documentado |

### Deuda técnica / pendientes
- 3 casos de `tmp_path` bloqueados en runner Windows (limitación del runner de pruebas, no del producto). **PENDIENTE**.
- E2E cross-browser Firefox/WebKit y steps `release` (nginx, JS syntax, package.zip, migrate, seeds, `--deploy`)
  no ejecutados en esta sesión (perfil `release`). **PENDIENTE / NO VERIFICADO**.
- Ejecución real de workers Celery/beat (+ tareas de backup/QA periódicas) no verificada en runtime. **NO VERIFICADO**.
- Caminos: N+1 residuales fuera del set de vehículos/dashboards no instrumentados a nivel global (solo
  `tests/performance` para staff pages). **PENDIENTE** de barrido si se desea presupuesto de queries global.
- Revisión visual humana (`VISUAL APPROVED`) y credenciales de cuentas QA reales: **PENDIENTE**.

---

## 12. Concurrencia e integridad

- Ventas, reservas, pagos, conversiones de leads y movimiento de stock prueban estados, historial e
  integridad de stock. **VERIFICADO** (suites D2/D4/D7).
- **Conversión de leads bajo concurrencia** (PostgreSQL-only): `apps/leads/tests/test_conversion_concurrency_v110.py`
  **4 passed** contra PostgreSQL real aislado (D8). En SQLite los mismos 3 tests fallan por locking/serialización —
  es comportamiento de ambiente documentado, **no defecto de producto**.
- El resto de la suite en SQLite: 2116 passed + 2 skipped (D7); **2119 passed + 24 skipped** sobre
  PostgreSQL aislado (D8; los 22 skipped son `e2e` que corren en el paso E2E).

---

## 13. Rendimiento

- Instrumento de presupuesto de queries: `tests/performance/test_staff_page_query_budget.py` (budget 45).
  **VERIFICADO PASS** (D7/D8). Mejoras: reports 61→36q, admin 54→48q (medidas aisladas); N+1 de vehículos
  resuelto (no más consulta por modelo). Medidas absolutamente aisladas (fixture mínima); no son carga de un
  dataset grande real. **NO VERIFICADO** bajo volumen real de producción.

---

## 14. Testing y evidence de la iniciativa

- **EJECUCIÓN D8 (regresión completa, VERDE):** runner QA `full` − `static.ruff`, `django.check`,
  `migrations.drift`, `release.readiness`, `tests.smoke` (50p), `openapi.validate`, `tests.full`
  (**2119 passed, 24 skipped** en PG aislado), `dependencies.check`, `e2e.chromium` (**22/22**).
  **9/9 PASS**. Evidencia: `private/qa_reports/full-audit/d8-full-run/`.
- **Concurrencia PG real:** `test_conversion_concurrency_v110` **4 passed** directo contra `vinova_d8`. 
- **Visual D8:** `visual_audit` 2 passed — matriz **302 checkpoints** (13 roles × Light/Dark × 3 viewports,
  sin overflow, sin errores JS, `data-theme` OK) + **24 estados** 0 fallos + 0 notes (403 con tema) ;
  `ui_snapshot` **8/8**. Evidencia: `private/qa_reports/full-audit/d8-visual-audit/` y `d8-ui-snapshot/`.
- **Historial por fase (VERIFICADO en su momento):** D2 81 casos PASS · D3 13×23 rutas PASS (Chromium) ·
  D4 e2e 22/22 + runner full PG 9/9 (451p/22s) · D5 `tests/security` 1642 PASS + 1 SKIP · D6 visual
  302+24 0 fallos + snapshot 8/8 · D7 action-sweep 20/20 + perf PASS + 2116p/2s (SQLite) · D8 ver arriba.
- Comandos útiles:
  - Local: `DJANGO_SETTINGS_MODULE=config.settings.test python -m pytest ...` (usa SQLite; e2e con
    `VINOVA_E2E_ACTIVE=1` y `VINOVA_E2E_BROWSER=chromium`).
  - Runner: `python manage.py run_quality_checks --profile full --no-persist` con
    `VINOVA_QA_DATABASE_ADMIN_URL` + `VINOVA_QA_REDIS_URL` + `config.settings.test` (ver §15).
- Números de tests (recuento): 27 archivos `test*.py` en `tests/` (no-E2E) + 14 archivos E2E + suites en apps.
- Framework: pytest 9.1.1, pytest-django 4.12.0, playwright 1.60.0, `pyproject.toml` con marcadores `e2e`
  y contrato de lint para ruff.

---

## 15. QA automatizado (runner)

- **Perfiles:** `quick` (ruff, django.check, migrations.drift, release.readiness, smoke),
  `full` (+ openapi.validate, tests.full, dependencies.check, e2e.chromium),
  `release` (+ e2e.cross_browser con video, django.deploy (`--deploy`), database.migrate, seeds.idempotency,
  database.readiness, nginx.syntax, javascript.syntax, package.clean). **VERIFICADO** (config del runner).
- **Persistencia:** `QualityRun`/`QualityCheckResult`; retención 90 días; reportes JSON/HTML bajo
  `VINOVA_QA_REPORT_ROOT`. En el runner local de pruebas usar `--no-persist` (la tabla QA no existe en el
  sqlite de test). **VERIFICADO**.
- **Aislamiento:** base PostgreSQL aislada (nombre `vinova_qa_<12 hex>`), Redis aparte, runtime
  `root/run/qa`, `VINOVA_QA_MAX_CONCURRENT_RUNS=1`. **VERIFICADO** (D8).
- **E2E headless:** playwright chromium local (bundle 1223 instalado vía `python -m playwright install chromium`).
  Fallback legacy: `VINOVA_E2E_EXECUTABLE_PATH=%LOCALAPPDATA%\ms-playwright\chromium-1243\chrome-win64\chrome.exe`.

---

## 16. Contradicciones documentales detectadas

- `docs/ROLES_PERMISOS.md` omitía `superadmin` → **CORREGIDO (D1)** (doc alineado al seed real).
- `docs/QA_FULL_V200.md` registra una corrida histórica; no representa el estado actual → este documento
  es la fuente vigente (D9).
- README/scaffold antiguos describían roles/flags hoy implementados de forma distinta → verificado contra código.
- El presente master document era un borrador D0 (todo “PENDIENTE”) → **actualizado en D9** a su estado real
  (VERIFICADO/NO VERIFICADO/PENDIENTE).

---

## 17. Estado de auditoría y cierre

### Cobertura ejecutada
- **Roles auditados (13):** login, dashboard, rutas, tabs, denials, formularios, modales, acciones,
  exports, uploads, cambios de estado — matrices sintética (D3), de acción (D7) y visual (D6/D8).
- **Permisos y scopes:** estáticos (seed) + comportamiento (D2) + IDOR/ownership (D5) + APIs/exports/CSRF (D5).
- **Seguridad defensiva:** `tests/security` (9 suites, 1642 PASS). 
- **Flujos:** producto E2E 22/22 (ventas, clientes, vehículos, inventario, documentos, imports, privacidad,
  seguridad, roles, responsive) + action sweep.
- **Concurrencia:** PostgreSQL real (4/4 leads, D8). 
- **Responsive/theme:** 3 viewports × Light/Dark (visual + E2E), sin overflow en 320–1920 px.
- **Browser:** Chromium headless (D4/D8); Firefox/WebKit pendiente (perfil release).

### Estado final de la iniciativa
- Auditoría ejecutada D0–D8: **AUDIT COMPLETE WITH PENDING ITEMS** (ver §11 pendientes y NO VERIFICADOs,
  mayormente steps del perfil `release` y aprobación humana).
- `PUSH_AUTHORIZED`: **NO** · `VISUAL_APPROVED`: **PENDIENTE (requiere revisión humana)** ·
  `FINAL_HUMAN_REVIEW`: **PENDIENTE**.
- Reporte de cierre (closure flags y cobertura formal): `docs/VINOVA_PRO_FINAL_REPORT.md`.
