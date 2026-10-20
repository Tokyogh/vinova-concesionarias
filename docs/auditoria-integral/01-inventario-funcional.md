# B1 — Inventario funcional de VINOVA PRO

Fecha de corte: 2026-10-15
Base auditada: `823cfab` sobre `integration/lite-pro`
Fuente primaria: código, resolución de URLs, modelos cargados, seeds y pruebas. La documentación histórica solo se usó como contraste.

## Convención de estado

- **VERIFICADA:** existe un flujo coherente y tiene evidencia automatizada vigente.
- **PARCIAL:** una parte funciona, pero falta interfaz, integración o verificación necesaria.
- **DEFECTUOSA:** existe un defecto reproducible.
- **BLOQUEADA:** requiere credenciales, proveedor o entorno externo no disponible.
- **NO PROBADA:** existe código, pero esta auditoría aún no demostró su comportamiento.

## Huella comprobada

| Elemento | Resultado |
|---|---:|
| Apps propias instaladas | 27 |
| Modelos propios cargados | 85 |
| Patrones URL resueltos | 1.289, incluidos 485 de Django Admin y duplicados de formato de DRF |
| Migraciones propias numeradas | 57 |
| Archivos de rutas | 35 |
| Archivos de vistas | 48 |
| Archivos de servicios | 29 |
| Archivos de selectores | 26 |
| Archivos de formularios | 24 |
| Archivos de prueba | 133 |
| Funciones de prueba declaradas | 726, antes de parametrización |
| Casos recolectados en la corrida aislada | 2.482 |

`python manage.py check` terminó sin issues y `makemigrations --check --dry-run` no detectó drift. La suite aislada actual obtuvo **2.439 passed, 41 skipped y 2 failed**. Los dos fallos no corresponden a un flujo del producto: dos pruebas de settings de producción dependen de que el `.env` del desarrollador aporte una clave válida. Al ejecutar con `VINOVA_QA_IGNORE_PROJECT_ENV=1`, la guarda de producción rechaza correctamente la clave insegura por defecto. La corrección del arnés queda asignada a B5.

## Inventario por dominio

| Dominio | Responsabilidad y modelos | Interfaces y operaciones reales | Autorización y dependencias | Estado demostrado |
|---|---|---|---|---|
| `accounts` | Identidad, `PermissionCode`, `Role`, `User`, `UserRole`, `ClientInvitation`. | Login por email/usuario, logout POST, perfil/avatar, reset de contraseña, CRUD de usuarios, roles, activación, contraseña administrativa, registro/invitación cliente. | `accounts.manage_users`, `accounts.assign_roles`; alcance global o de sucursal; integra seguridad, auditoría, Customer y portal. | **VERIFICADA**; la vigencia de roles y el alcance se profundizan en B4. |
| `security_center` | Política, perfil 2FA, historial de contraseñas y sesiones activas. | Política, cambio de contraseña, alta/desactivación 2FA, códigos de respaldo, challenge, sesiones y revocación, reset administrativo. | `security.view/manage`; middleware de enforcement; depende de accounts, sesión, caché y auditoría. | **VERIFICADA**, con deuda histórica del challenge 2FA a reevaluar en B5. |
| `companies` | `Company`, identidad empresarial y colores. | Listado, alta, detalle y edición internos; API protegida. | `companies.manage`, solo permiso global. | **VERIFICADA** técnicamente. El modelo admite varias filas `Company`, pero no existe tenancy ni selección de tenant: PRO sigue siendo una instalación monocompañía. |
| `branches` | `Branch`, sede, tipo, dirección, contacto, servicios, publicación y coordenadas. | CRUD interno, API y directorio público `/instituciones/`; filtros, búsqueda, detalle y mapa. | `branches.manage` global; selector público exige empresa/sede activas, `is_public` y tipo permitido. | **PARCIAL**: datos y mapa funcionan; no existe fotografía por sede, solo imágenes estáticas por categoría. El recorrido completo se prueba en B3. |
| `enterprise` | `CompanyPublicSettings`, `ApprovalPolicy`. | Centro empresarial, perfil, branding, contacto, legales, sitio público y políticas. | `enterprise.manage`, `approvals.manage`. Alimenta contexto público y decisiones sujetas a aprobación. | **VERIFICADA** para configuración local; publicación externa no aplica. |
| `customers` | `Customer`, intereses y notas. `Customer.account` vincula expediente y cuenta. | CRUD, estado, notas, intereses, invitación y asociación explícita de cuenta. | `customers.view/manage`, ownership por sucursal; integra leads, ventas, vehículos, documentos y portal. | **VERIFICADA**; asociación heredada segura cubierta por regresión. |
| `portal` | Capa privada del cliente sin modelos duplicados. | Dashboard, perfil/configuración, vehículos, documentos/descargas, facturas/PDF, servicios, notificaciones/archivo y canje de código. | Requiere `portal.access`, cuenta activa, Customer elegible y ownership; denegación controlada si falta expediente. | **VERIFICADA** en Chromium y pruebas de ownership; postventa depende del flag. |
| `vehicles` | Marca, modelo, vehículo, medios, recursos, especificaciones, destacados, códigos de vinculación y `CustomerVehicle`. | Catálogo público, detalle/modal, favorito local, canje; CRUD interno, publicación/estado, medios, catálogos, código generar/revocar, desvincular y transferir garaje. | `vehicles.view/manage/publish/link_codes/delete_permanent`; scope de sucursal y ownership cliente. | **VERIFICADA**. El borrado permanente existe como permiso sensible; su política se revisa en B4/B5. |
| `inventory` | Categoría, ítem, stock por sucursal y movimiento. | CRUD, categorías, altas/bajas, ajustes, movimientos, transferencias y bajo stock. | `inventory.view/manage_stock`; bloqueo transaccional y scope de sucursal. | **PARCIAL**: flujos principales probados; `update_minimum_stock()` no tiene consumidor ni interfaz detectables. |
| `leads` | Lead, actividad y prueba de manejo. | Captura pública con rate limit; listado/pipeline, CRUD, estado, actividad, asignación, test drive, conversión a Customer, cotización y exportación. | `leads.view/manage/assign/export`; scopes de sucursal y transacciones. | **VERIFICADA**; concurrencia PostgreSQL se revalida en B12. |
| `sales` | Venta/cotización/reserva, líneas, pagos e historial. | CRUD operativo, transiciones, líneas, pago, anulación de pago y atención. | `sales.quote/reserve/sell`; branch scope; integra inventario, Customer, vehículo, factura y aprobaciones. | **VERIFICADA** en suite; ciclo contable completo se vuelve a trazar en B3. |
| `invoices` | Secuencia, comprobante, líneas, aplicaciones de pago e historial. | Lista, creación desde venta, líneas, emisión/acciones, aplicación de pago, impresión y PDF; API de lectura. | `invoices.view/issue/manage/void`; scope de sucursal y estados. | **VERIFICADA** para factura interna. SRI queda excluido del alcance. |
| `post_sales` | Orden, líneas e historial de servicio. | Listado, creación, detalle, línea, estado y actualización operativa; exposición controlada al portal. | `post_sales.view/manage` y `VINOVA_MODULE_POST_SALES_ENABLED`; OFF devuelve 404 también por URL directa. | **VERIFICADA cuando ON y OFF** por pruebas; deshabilitada por defecto. No hay recordatorios automáticos. |
| `documents` | Categorías, recursos reutilizables y documentos privados. | Biblioteca, CRUD/archivo, descarga privada y datos de catálogo. | `documents.view/manage/download_private`; ownership/scope; almacenamiento local o S3-compatible privado. | **VERIFICADA** con backend local; proveedor S3 real **BLOQUEADO** a staging. |
| `notifications` | Plantillas, mensajes, destinatarios, preferencias, campañas y snapshots. | Bandeja/enviados, composición, archivo, plantillas, segmentación/cálculo/mensaje/confirmación de campañas; API. | `notifications.*`, `campaigns.*`; branch scope, consentimiento y tareas. | **VERIFICADA** en modo local/eager; entrega SMTP/Celery externa **BLOQUEADA**. |
| `reports` | `ReportExportJob`. | Dashboard, detalle, impresión y exportación. | `reports.view`, además de permisos de datasets asociados. | **VERIFICADA** con datos sintéticos; carga real **NO PROBADA**. |
| `analytics` | `VehicleInteraction`. | Dashboard comercial, perfiles de usuario/cliente y exportación BI. | `analytics.view/export`; reutiliza selectores con scope. | **VERIFICADA** por pruebas de permisos y datasets. |
| `imports` | Lote y fila de importación. | Plantilla, carga, prevalidación, revalidación, confirmación e historial. | `imports.manage`; validación, branch scope y transacción. | **VERIFICADA**; no se autoriza importación histórica LITE. |
| `privacy` | Consentimiento, solicitud, exportación, retención y anonimización. | Solicitud pública, dashboard/CRUD, exportar, descargar, anonimizar y políticas de retención. | `privacy.view/manage/export/anonymize`; estados y auditoría. | **VERIFICADA** con datos sintéticos; criterios legales finales requieren revisión humana. |
| `audit` | Log inmutable de eventos y alertas de seguridad. | Filtros, detalle, exportación, integridad, alertas y resolución. | `audit.view/export/manage_alerts`; middleware y servicios transversales. | **VERIFICADA**; los admins Django no permiten mutación ordinaria de logs. |
| `api` | Scopes, clientes API, idempotencia, logs, webhooks, eventos y entregas. | `/api/`, `/api/v1/`, OpenAPI, administración interna, rotación/revocación, prueba de webhook, BI y export contable. | Sesión o bearer hasheado, scopes, permisos `integrations.*`, throttling, idempotencia y filtro de sucursal. | **VERIFICADA** localmente; entrega a proveedor externo y TLS **BLOQUEADOS**. |
| `continuity` | Políticas, backups y simulacros de restore. | Dashboard, políticas, crear/verificar/descargar backup, preparar/completar restore y update center. | `continuity.view/manage/restore`; almacenamiento privado, firmas/manifiestos y Celery. | **VERIFICADA** en ejercicios aislados previos; operación programada real **NO PROBADA** en esta auditoría. |
| `quality` | Ejecuciones y resultados QA. | Historial, detalle, descarga y lanzamiento de perfiles cerrados; API/tareas. | `quality.view/run`, flags QA, límite de concurrencia y cola dedicada. | **VERIFICADA** para runner; automatización periódica real **NO PROBADA**. |
| `dashboard` | Shell, widgets, búsqueda universal y asistente determinista. | Dashboard adaptado a rol, preferencias, navegación, Ctrl+K, búsqueda y rutas históricas compatibles. | Registro filtra por permisos/módulos y vuelve a aplicar selectors en backend. | **VERIFICADA** en E2E; aprobación visual humana sigue pendiente. |
| `help_center` | Categorías, artículos, checklists, progreso y preferencia. | Inicio, búsqueda, artículo/impresión, checklist, toggle y modo capacitación. | `help.view/manage`; contexto por rol. | **VERIFICADA**. |
| `common` | Bases abstractas, navegación, lookup, filtros, storage, health, logging y utilidades. | Health live/ready, lookup autorizado y soporte transversal. | Deny-by-default delegado a consumidores; redacción de logs. | **VERIFICADA** como infraestructura compartida. |
| `sri_integration` | Configuración, establecimientos y secuencias SRI. | Interfaces y API existentes para configuración. | `sri.manage`. | **NO PROBADA / EXCLUIDA EXPRESAMENTE** de esta consolidación; no se ampliará ni presentará como capacidad certificada. |

## Relaciones y recorridos principales

```text
User ── UserRole ── Role ── PermissionCode
  │          └──── Branch scope
  └── Customer.account ── CustomerVehicle ── Vehicle

Lead ──> Customer ──> SaleRecord ──> InvoiceRecord
                    ├──> SalePayment
                    └──> Vehicle / Branch

InventoryItem ── BranchStock ── StockMovement
Branch ──> directorio público ──> coordenadas ──> MapTiler/MapLibre

PrivateDocument ── Customer/Vehicle/Branch ──> almacenamiento privado
NotificationMessage ── NotificationRecipient ──> User/Customer
```

Los límites de autorización se apoyan en `accessible_branch_ids()`, selectores por dominio, ownership de cliente y permisos vigentes. Las vistas no deben construir un queryset global y confiar solo en ocultar controles.

## Configuración e integraciones

| Mecanismo | Configuración real | Estado |
|---|---|---|
| PostgreSQL | `DATABASE_URL`, conexiones persistentes y health checks. | Local activo; concurrencia se certifica en B12. |
| Redis | Caché y broker/result de Celery. | Local activo. |
| Celery | Colas `default`, `backups`, `webhooks`, `qa`; beat para expiraciones, heartbeat, backups y QA. | Configurado; ejecución periódica externa pendiente. |
| Email | SMTP parametrizable; Mailpit local. | Local verificable; entrega real pendiente. |
| Cloudinary | Avatar público con timeout y fallback local. | Integrado; credenciales reales pendientes. |
| S3-compatible | Documentos privados con URLs firmadas y fallback local. | Integrado; proveedor real pendiente. |
| MapTiler/MapLibre | Clave pública, CSP limitada, coordenadas verificadas y fallback. | Verificado localmente con clave aceptada; restricciones de dominio/staging pendientes. |
| Webhooks | Firma, reintento, logs, allowlist SSRF y cola dedicada. | Pruebas locales; receptor externo pendiente. |
| OpenAPI/DRF | Schema y Swagger; docs públicas en local, privadas en producción. | Verificado estáticamente y por pruebas. |

Se revisaron 45 settings propios/almacenamiento relevantes y todos tienen al menos un consumidor adicional a su definición; no se detectó un flag completamente inefectivo mediante referencia estática.

## Brechas y elementos huérfanos confirmados

| ID | Clasificación | Evidencia | Prioridad / destino |
|---|---|---|---|
| B1-01 | **PARCIAL** | `Branch` no tiene campo ni backend de fotografía; el directorio usa assets estáticos por categoría. | Comparar con LITE en B2 y decidir en B3 si es defecto puntual o capacidad nueva. |
| B1-02 | **PARCIAL** | `update_minimum_stock()` aplica permiso, lock, validación y auditoría, pero no tiene referencias fuera de su definición. | B3: confirmar si falta UI/API y priorizar. |
| B1-03 | **PARCIAL** | `user_operational_branch()` no tiene consumidores detectados. | B3/B8: conservar hasta determinar intención; no borrar automáticamente. |
| B1-04 | **DEFECTUOSA** | Dos pruebas de flags de cookies de producción dependen del secreto local y fallan en un runner que ignora `.env`. | B5: aislar tests con configuración sintética sin debilitar la guarda. |
| B1-05 | **REEMPLAZABLE** | La documentación maestra fechada 2026-10-07 omite `portal`, modelos de garaje y cambios LITE→PRO posteriores; sus cifras de migraciones/tests ya no son vigentes. | B6/B7: sustituir como fuente vigente, conservar valor histórico hasta cerrar referencias. |
| B1-06 | **NO PROBADA** | No se demostró entrega real de Celery/SMTP, proveedores Cloudinary/S3, TLS, Nginx vivo ni carga productiva. | Gates externos B12; nunca inferirlos desde unit tests. |

No se confirmó en este bloque un botón visible sin backend. La ausencia de una interfaz para mínimos de stock sí quedó demostrada por análisis de referencias del servicio. Los escaneos estáticos no sustituyen los recorridos B3/E2E.

## Conclusión B1

VINOVA PRO posee una arquitectura empresarial amplia y mayormente cubierta por pruebas, pero el inventario vigente no coincide con la documentación maestra anterior. El estado global de B1 es **COMPLETADO CON BRECHAS REGISTRADAS**: no hay bloqueo para continuar a la comparación LITE→PRO; B1-01 a B1-06 quedan trazados a los bloques que deben resolverlos o mantenerlos como riesgo explícito.
