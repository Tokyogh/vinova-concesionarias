# B4 — Matriz canónica de roles y permisos

Fecha de comprobación: 2026-10-15
Fuente ejecutable: `apps/accounts/management/commands/seed_roles.py`
Contrato automatizado: `tests/security/test_integral_rbac_matrix.py`
Contrato de rutas: `tests/deployment_smoke/role_contract.py`

## Semántica de autorización

La autorización efectiva no depende solo del nombre del rol. Una celda está
permitida cuando concurren todas estas condiciones:

1. la cuenta está autenticada y activa;
2. el rol y su asignación están activos;
3. `starts_at` ya comenzó y `expires_at` todavía no venció;
4. el rol contiene el `PermissionCode` requerido;
5. si el recurso pertenece a una sucursal, la asignación es global
   (`UserRole.branch = NULL`) o coincide con la sucursal del recurso;
6. los selectores de cada dominio limitan el queryset antes de resolver el
   objeto, por lo que un recurso ajeno responde 404 en vez de revelar su
   existencia;
7. el módulo funcional está habilitado.

Una asignación global produce alcance `TODAS`; una asignación a sucursal
produce alcance `PROPIA`; la ausencia de una asignación elegible produce
`NINGUNA`. Todo permiso no enumerado para un rol se considera **DENEGADO**.
Los flags Django `is_staff` e `is_superuser` no se asignan a cuentas QA de rol.
El superusuario activo conserva el bypass explícito de emergencia; una cuenta
superusuario inactiva queda denegada en las APIs de dominio.

## Dimensiones permiso × operación × módulo × recurso

La tabla contiene los 63 códigos vigentes. “Sucursal” describe cómo se aplica
el alcance cuando el recurso tiene `branch`; no convierte por sí sola un rol
en global.

| Módulo | Recurso | Operaciones / PermissionCode | Sucursal |
|---|---|---|---|
| dashboard | panel interno | ver: `dashboard.view` | perfil derivado |
| accounts | usuarios y roles | gestionar usuarios: `accounts.manage_users`; asignar roles: `accounts.assign_roles` | propia/todas |
| companies | empresa | gestionar: `companies.manage` | global |
| branches | sucursales/instituciones | gestionar: `branches.manage` | global |
| vehicles | vehículos y vínculos | ver: `vehicles.view`; gestionar: `vehicles.manage`; publicar: `vehicles.publish`; códigos: `vehicles.link_codes`; eliminación permanente: `vehicles.delete_permanent` | propia/todas |
| inventory | artículos, stock y movimientos | ver: `inventory.view`; gestionar stock: `inventory.manage_stock` | propia/todas |
| customers | expedientes cliente | ver: `customers.view`; gestionar: `customers.manage` | propia/todas |
| sales | cotizaciones, reservas y ventas | cotizar: `sales.quote`; reservar: `sales.reserve`; vender: `sales.sell` | propia/todas |
| invoices | comprobantes | ver: `invoices.view`; emitir: `invoices.issue`; gestionar: `invoices.manage`; anular: `invoices.void` | propia/todas |
| documents | biblioteca y archivos privados | ver: `documents.view`; gestionar: `documents.manage`; descargar privado: `documents.download_private` | propia/todas |
| notifications | mensajes y plantillas | ver: `notifications.view`; enviar: `notifications.send`; gestionar plantillas: `notifications.manage_templates` | propia/todas |
| reports | reportes | ver: `reports.view` | propia/todas |
| imports | lotes de importación | gestionar: `imports.manage` | propia/todas |
| data | datasets operativos | exportar: `data.export` | propia/todas |
| enterprise | centro empresarial | gestionar: `enterprise.manage` | global |
| sri | configuración SRI | gestionar: `sri.manage` | global; módulo excluido del producto actual |
| approvals | políticas de aprobación | gestionar: `approvals.manage` | global |
| audit | eventos y alertas | ver: `audit.view`; exportar: `audit.export`; alertas: `audit.manage_alerts` | propia/todas |
| campaigns | campañas | ver: `campaigns.view`; preparar: `campaigns.manage`; confirmar envío: `campaigns.send` | propia/todas |
| leads | CRM y leads | ver: `leads.view`; gestionar: `leads.manage`; asignar: `leads.assign`; exportar: `leads.export` | propia/todas |
| analytics | analítica comercial | ver: `analytics.view`; exportar: `analytics.export` | propia/todas |
| continuity | backups y restauración | ver: `continuity.view`; gestionar: `continuity.manage`; restaurar: `continuity.restore` | global |
| privacy | solicitudes y datos personales | ver: `privacy.view`; gestionar: `privacy.manage`; exportar: `privacy.export`; anonimizar: `privacy.anonymize` | propia/todas |
| security | políticas y 2FA | ver: `security.view`; gestionar: `security.manage` | propia/todas |
| integrations | API y webhooks | ver: `integrations.view`; gestionar: `integrations.manage` | global |
| help | ayuda y capacitación | ver: `help.view`; gestionar: `help.manage` | global |
| quality | ejecuciones QA | ver: `quality.view`; ejecutar: `quality.run` | global |
| post_sales | órdenes de postventa | ver: `post_sales.view`; gestionar: `post_sales.manage` | propia/todas |
| portal | portal privado cliente | acceder: `portal.access` | ownership por `Customer.account` |

## Matriz rol × permiso

Las listas son exhaustivas: cualquier código no incluido está denegado. El
número entre paréntesis es la cantidad comprobada contra la base sembrada.

| Rol | Alcance operativo esperado | Permisos permitidos |
|---|---|---|
| `superadmin` (63) | todas; rol del sistema, sin flag Django obligatorio | todos los 63 códigos vigentes |
| `admin_general` (63) | todas | todos los 63 códigos vigentes |
| `admin_sucursal` (35) | sucursal obligatoria | `dashboard.view`, `vehicles.view`, `vehicles.manage`, `vehicles.link_codes`, `inventory.view`, `inventory.manage_stock`, `customers.view`, `customers.manage`, `sales.quote`, `sales.reserve`, `sales.sell`, `invoices.view`, `invoices.issue`, `documents.view`, `documents.manage`, `documents.download_private`, `notifications.view`, `notifications.send`, `notifications.manage_templates`, `campaigns.view`, `campaigns.manage`, `campaigns.send`, `reports.view`, `imports.manage`, `data.export`, `leads.view`, `leads.manage`, `leads.assign`, `leads.export`, `analytics.view`, `analytics.export`, `privacy.view`, `privacy.manage`, `privacy.export`, `help.view` |
| `gerente_comercial` (22) | global o asignado explícitamente | `dashboard.view`, `vehicles.view`, `customers.view`, `sales.quote`, `sales.reserve`, `sales.sell`, `invoices.view`, `documents.view`, `documents.download_private`, `notifications.view`, `notifications.send`, `campaigns.view`, `campaigns.manage`, `campaigns.send`, `reports.view`, `leads.view`, `leads.manage`, `leads.assign`, `leads.export`, `analytics.view`, `analytics.export`, `help.view` |
| `jefe_inventario` (9) | sucursal obligatoria | `dashboard.view`, `vehicles.view`, `vehicles.manage`, `inventory.view`, `inventory.manage_stock`, `reports.view`, `imports.manage`, `data.export`, `help.view` |
| `vendedor` (12) | sucursal obligatoria | `dashboard.view`, `vehicles.view`, `customers.view`, `customers.manage`, `sales.quote`, `sales.reserve`, `documents.view`, `notifications.view`, `notifications.send`, `leads.view`, `leads.manage`, `help.view` |
| `asesor_postventa` (10) | sucursal obligatoria | `dashboard.view`, `customers.view`, `vehicles.link_codes`, `documents.view`, `documents.download_private`, `notifications.view`, `notifications.send`, `post_sales.view`, `post_sales.manage`, `help.view` |
| `facturacion` (12) | sucursal obligatoria | `dashboard.view`, `sales.sell`, `invoices.view`, `invoices.issue`, `invoices.manage`, `invoices.void`, `documents.view`, `documents.manage`, `documents.download_private`, `notifications.view`, `notifications.send`, `help.view` |
| `bodega` (4) | sucursal obligatoria | `dashboard.view`, `inventory.view`, `inventory.manage_stock`, `help.view` |
| `marketing` (14) | global o asignado explícitamente | `dashboard.view`, `vehicles.view`, `vehicles.manage`, `vehicles.publish`, `customers.view`, `notifications.view`, `notifications.send`, `notifications.manage_templates`, `campaigns.view`, `campaigns.manage`, `campaigns.send`, `imports.manage`, `analytics.view`, `help.view` |
| `soporte_cliente` (10) | global o asignado explícitamente | `dashboard.view`, `customers.view`, `documents.view`, `notifications.view`, `notifications.send`, `leads.view`, `leads.manage`, `privacy.view`, `privacy.manage`, `help.view` |
| `auditor` (23) | global o asignado explícitamente; solo lectura salvo exportaciones autorizadas | `dashboard.view`, `vehicles.view`, `inventory.view`, `customers.view`, `sales.quote`, `invoices.view`, `documents.view`, `notifications.view`, `reports.view`, `data.export`, `audit.view`, `audit.export`, `leads.view`, `leads.export`, `analytics.view`, `analytics.export`, `continuity.view`, `privacy.view`, `privacy.export`, `security.view`, `integrations.view`, `quality.view`, `help.view` |
| `cliente` (1) | ownership por expediente | `portal.access` |

## Evidencia automatizada

| Condición | Evidencia |
|---|---|
| matriz exacta permitida/denegada para 13 roles × 63 permisos | `test_integral_rbac_matrix.py::test_seeded_role_has_exact_permission_contract` |
| rol revocado, futuro, expirado y rol desactivado | `test_integral_rbac_matrix.py` y `test_d5_authorization_matrix.py` |
| cuenta inactiva, incluida superusuario inactivo | `test_integral_rbac_matrix.py::test_inactive_account_has_no_domain_permission_or_scope` |
| sucursal y recurso ajenos | `test_d5_authorization_matrix.py`, suites de integridad por dominio y E2E de roles |
| cliente sin expediente | `apps/portal/tests/test_portal.py` y `apps/accounts/tests/test_client_access.py` |
| módulo deshabilitado | `tests/e2e/test_09_roles.py` y pruebas de `apps/modules` |
| GET, POST, mutaciones y URL directa | `test_d7_role_action_sweep.py`, pruebas D5 y contrato deployment-smoke |
| CSRF, escalación y exportaciones | `test_d5_csrf.py`, `test_d5_privilege_escalation.py`, `test_d5_export_authorization.py` |

Resultados ejecutados en este bloque:

- contrato RBAC focal: **26 passed**;
- Chromium representativo de perfiles y aislamiento: **2 passed** en 144,36 s;
- el escenario completo visitó 23 rutas por cada uno de los 13 roles, además
  de dashboard, ownership de vehículo y módulo postventa OFF;
- Ruff focal: sin incidencias;
- Django check con settings de prueba: sin incidencias.

## Ambigüedades y decisiones conservadas

- Los seis roles operativos listados como “sucursal obligatoria” no pueden ser
  asignados globalmente mediante el servicio. Los demás roles admiten una
  asignación global o explícita a sucursal; esa política preexistente se
  conserva y no se amplió.
- `sri.manage` permanece en el catálogo histórico/canónico, pero SRI está
  expresamente fuera del alcance del producto actual. No se interpretó la
  presencia del código como una capacidad operativa habilitada.
- `sales.quote` permite al auditor abrir superficies de ventas definidas por el
  contrato actual. No se modificó esa decisión empresarial durante la auditoría.
- La habilitación de módulo es una condición adicional: un permiso no fuerza la
  exposición de una ruta si el módulo está OFF.

## Corrección aplicada

`User.active_role_assignments()`, `User.has_perm_code()` y los helpers comunes
de alcance/autoridad ahora niegan explícitamente a cuentas inactivas. Esto
cierra consultas de autorización hechas directamente por servicios, fuera del
flujo de login, sin cambiar la matriz de permisos ni el ownership.
