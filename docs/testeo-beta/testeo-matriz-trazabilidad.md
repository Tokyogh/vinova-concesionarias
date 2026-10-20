# Testeo beta — matriz de trazabilidad

La matriz enlaza capacidades reales, permisos, casos manuales y evidencia automatizada. Los rangos remiten a las guías modulares; la guía de rol decide qué casos corresponden a cada evaluador.

| Requisito | Permisos / condición | Casos manuales | Evidencia automatizada principal |
|---|---|---|---|
| autenticación y sesión | cuenta activa | `AS-001..AS-006` | cuentas, security center, D5 auth/CSRF |
| permisos vigentes y URL directa | 63 códigos; rol activo/vigente | `AS-007..AS-010`, casos `ROL-*` | `test_integral_rbac_matrix.py`, D5/D7, E2E roles |
| acceso Staff basado en riesgo | política `off/monitor/enforce`; red, 2FA y aprobador | `AS-011..AS-015` | `test_staff_adaptive_access.py` |
| empresa y configuración | `companies.manage`, `enterprise.manage`, `approvals.manage` | `ESP-001..ESP-003` | enterprise/companies tests |
| sucursales e instituciones | `branches.manage`; publicación activa | `ESP-004..ESP-012` | branches tests, cookies y flujo B3 |
| catálogo/garaje/códigos | `vehicles.*`, `portal.access`, datos propios | `VEH-001..VEH-009` | vehicles, portal garage, E2E |
| clientes y cuenta | `customers.*`, `portal.access` | `CP-001..CP-010` | customer scope y client access |
| inventario, stock y repuestos públicos | `inventory.*`; sucursal; flag público | `INV-001..INV-012` | inventory services/scope/concurrency/public catalog |
| CRM, leads y venta | `leads.*`, `sales.*` | `CV-001..CV-012` | leads/sales lifecycle y D7 |
| comprobantes y pagos | `invoices.*`; venta/sucursal | `FD-001..FD-007` | invoices y portal invoice tests |
| documentos privados | `documents.*`; relación con el titular | `FD-008..FD-012` | document scope/download/security |
| postventa opcional | `post_sales.*`; módulo ON/OFF | `PN-001..PN-005` | post_sales y module-flag tests |
| mensajes y campañas | `notifications.*`, `campaigns.*`, consentimiento | `PN-006..PN-013` | notification/campaign tests |
| reportes, BI y analítica | `reports.view`, `data.export`, `analytics.*` | `RAI-001..RAI-007` | reports/analytics/export authorization |
| importaciones | `imports.manage`; confirmar explícitamente | `RAI-008..RAI-014` | imports parsing/application/scope/limits |
| privacidad y cookies | `privacy.*`; elección opcional y verificación | `PA-001..PA-008`, `PA-014..PA-017` | privacy services, cookie preferences y D5 |
| auditoría | `audit.*`; hash y redacción | `PA-009..PA-013` | audit integrity/resilience/export |
| API y webhooks | `integrations.*`; permisos, HMAC y destinos seguros | `IC-001..IC-010`, `IC-016` | API integrations/BI/security |
| continuidad y archivos | `continuity.*`; gate no productivo | `IC-011..IC-015`, `IC-017..IC-018` | continuity archive/transfer/release |
| módulos ON/OFF | permiso + feature flag | `QAC-001..QAC-003` | optional module/E2E role tests |
| QA, ayuda y responsive | `quality.*`, `help.*`; viewports | `QAC-004..QAC-010` | quality runner, help, Playwright/a11y |
| correcciones funcionales F17 | `portal.access`, `vehicles.*`, `help.*`; acceso a datos propios (también llamado *ownership*) y viewports | `FCR-001..FCR-015` | regresiones F17, E2E responsive y `test_12_functional_maps.py` |

## Cobertura negativa común

Cada guía de rol incluye al menos una URL no autorizada y, cuando corresponde, un recurso de otra sucursal. `cliente` añade acceso horizontal entre dos expedientes. Las mutaciones deben confirmar CSRF, persistencia y evento de auditoría cuando el flujo lo define.
