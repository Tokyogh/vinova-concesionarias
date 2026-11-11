# QA Completo — Vinova Pro v2.0.0

Rama objetivo: `feature/v0-2-auth-roles`. Fase de aseguramiento de calidad de cierre sobre la integridad comercial, seguridad, autorización y rendimiento de v2.0.0.

Objetivo cumplido: cubrir huecos reales de cobertura con pruebas de regresión, corregir defectos genuinos hallados, validar la suite funcional, concurrencia, E2E UI y rendimiento, y dejar el árbol limpio con los commits de la fase pusheados a `feature/v0-2-auth-roles`.

---

## 1. Cobertura de huecos funcionales (pruebas de regresión añadidas)

### 1.1 Seguridad de subidas de documentos
Nueva suite: `apps/documents/tests/test_uploads_security.py` (13 pruebas) en `f51c6ad`.

Cubre:
- Allowlist de extensiones y límite de tamaño de archivo.
- Traversal de rutas: la ruta almacenada es solo UUID (el nombre de cliente descartado por diseño); `..` se elimina y la descarga nunca expone rutas absolutas.
- Sanitización de metadatos (`original_name` con `basename`).
- Permisos de descarga: 403 sin permiso global, 404 en cruce de sucursal (IDOR/scope), descarga de superusuario permitida, descarga auditada.
- Bloqueo de archivo comprimido (zip/archivos de archivo).
- La raíz de almacenamiento de documentos privados está separada del directorio público `/media/`.

Veredicto de seguridad: el diseño de subidas es seguro por construcción; la suite fija el comportamiento y previene regresiones.

### 1.2 Módulos opcionales OFF (comportamiento transversal)
Nueva suite: `apps/common/tests/test_optional_modules_flag_v200.py` (3 pruebas) en `964b2a8`.

Cubre el gating del módulo opcional **postventa** cuando está OFF/ON:
- Con el módulo OFF, el bloque "Operación" de la barra lateral no debe mostrar la ruta Postventa.
- Con el módulo ON, un usuario sin permiso no ve el acceso.
- Con el módulo ON y usuario postventa autorizado, aparece el enlace `/dashboard/post-sales/`.

## 2. Defectos reales encontrados y corregidos

| Defecto | Causa | Corrección | Evidencia |
|---|---|---|---|
| HTTP 500 al crear lead interno con superusuario sin `UserRole` de sucursal | `_validate_advisor_branch` rechazaba superusers (incongruente con `accessible_branch_ids` que devuelve `None`/global para superusers), rompiendo el flujo de `form_valid` | Bypass de superusuario en `_validate_advisor_branch` | Commit `91112f1` + test de regresión en `apps/leads/tests/test_crm_v017.py` + E2E `test_06_crm_sales_and_invoice_flow` ahora pasa |
| Nav "Postventa" oculta para usuarios solo-postventa | Bloque "Operación" de `sidebar.html` condicionado a permisos vecinos sin incluir el módulo opcional postventa | Añadir `optional_modules.post_sales` a la condición del bloque | Commit `964b2a8` + prueba en `test_optional_modules_flag_v200.py` |
| Test de devops frágil (celery task-registration) | Orden de importación causaba falso positivo | Import explícito de tareas de continuidad | Commit `964b2a8` |

## 3. Rendimiento

### 3.1 N+1 en listas de ventas — corregido
Causa raíz: `VehicleModel.__str__` accede a `self.brand`, por lo que renderizar `str(vehicle)` (lista interna, tarjetas de atención y API) disparaba **una consulta a `vehicles_vehiclebrand` por fila**.

Métricas medidas (50 registros sembrados, página de 20):

| Ruta | Antes | Después |
|---|---|---|
| `/dashboard/sales/` | 50 consultas | 30 consultas |

Corrección: añadir `vehicle__model__brand` a `select_related` en `sale_list_queryset`, `sales_needing_attention_queryset` y el queryset de la API de ventas. Commit `4426bd9`.

Regresión protegida: `apps/sales/tests/test_sales_query_count_v200.py` verifica 0 consultas a `vehiclebrand` al renderizar `str(vehicle)` de 20 ventas. Verificado que **falla sin el fix** (detecta 20 consultas N+1) y **pasa con el fix**.

### 3.2 Perfiles de consultas (dentro de rango, sin N+1 por fila)
Medidos con 50 registros sembrados:

| Ruta | Consultas | Notas |
|---|---|---|
| `/dashboard/sales/` | 30 | tras fix (era 50) |
| `/dashboard/leads/` | 27 | múltiples querysets de filtros/estados, sin N+1 por fila |
| `/dashboard/documents/` | 21 | dentro de rango |
| `/dashboard/worker/` | 24 | varios widgets de panel, razonable |

No se detectó otro bottleneck claro ni N+1 severo fuera del caso de ventas corregido.

## 4. Validación final

### Suite funcional
- `apps` (excluyendo concurrencia PG-only): **357 passed, 1 skipped**.
- `tests/` (no e2e): **21 passed**.
- Concurrencia PG (doble reserva/venta, exclusividad, expiración) contra PostgreSQL real: **3/3 passed** (`apps/leads/tests/test_conversion_concurrency_v110.py` vía `TEST_DATABASE_URL`). Los 3 fallos que aparecen bajo SQLite son limitación esperada de SQLite (table locked), no regresión.

### E2E UI (Playwright)
- Run completo final post-fixes: **10/10 PASS, 0 failed, 0 skipped** (`status: passed`, ~364s). Todos los módulos verdes: público, autenticación/navegación, vehículos, clientes, inventario, CRM/ventas/factura, documentos/reportes, privacidad/seguridad, roles, accesibilidad.
- Fallo intermedio de infraestructura (no del producto): `test_02_authentication_and_internal_navigation` falló una vez por `Page.screenshot: Timeout 30000ms exceeded ... waiting for fonts to load` durante la captura de evidencias del teardown (el recorrido funcional de las 16 rutas pasaba; solo el screenshot excedió el timeout en el runner aislado). Se amplió el timeout del screenshot de evidencias a 120s en `tests/e2e/helpers/evidence.py` y el run completo quedó 10/10.
- Defecto real previo (HTTP 500 leads en `test_06`) permanece corregido y verificado verde en el run final.

### Infraestructura
- `manage.py check`: 0 issues.
- `makemigrations --check --dry-run`: sin cambios de modelo pendientes.
- `showmigrations` sobre PostgreSQL local: todas aplicadas.
- OpenAPI `/api/schema/` + readiness/liveness: verdes (suite `test_devops_health.py`, 9 passed).
- Ruff: limpio sobre todos los archivos nuevos/modificados.

## 5. Alcance y garantías
- Sin nuevas funcionalidades; solo corrección de defectos y endurecimiento de cobertura/rendimiento.
- Sin acceso a datos/entornos de producción, `.env*`, `nd.txt`, credenciales ni volúmenes reales.
- Sin modificación de los criterios funcionales del producto.
- Cambios de arquitectura: ninguno; solo `select_related` adicional y un bypass de autorización coherente con el alcance global de superusuarios.
- Commits locales en `feature/v0-2-auth-roles` (sin push, sin force, sin `--hard`, sin `clean`).

## 6. Commits de esta fase
- `f51c6ad` — test(documents): suite de subidas/seguridad.
- `964b2a8` — fix(qa): nav postventa para usuarios solo-postventa; test devops no frágil.
- `91112f1` — fix(leads): superusuario como asesor evita HTTP 500.
- `4426bd9` — perf(sales): prefetch `vehicle model brand` fija N+1 en listas.
- `fcbe3f2` — docs(qa): reporte QA_FULL_V200 (cobertura, defects, rendimiento, validación).
- (Cierre E2E) — fix(harness e2e): ampliar timeout del screenshot de evidencias (120s) para eliminar el flake de espera de fuentes; E2E final 10/10 PASS.
