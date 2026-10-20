# Testeo beta — rol Administración de sucursal

## Objetivo

Validar manualmente el contrato del rol `admin_sucursal` sin ampliar privilegios ni alcance.

## Rol, permisos y alcance

- Código: `admin_sucursal`.
- Alcance esperado: Sucursal obligatoria.
- Permisos: `dashboard.view`, `vehicles.view`, `vehicles.manage`, `vehicles.link_codes`, `inventory.view`, `inventory.manage_stock`, `customers.view`, `customers.manage`, `sales.quote`, `sales.reserve`, `sales.sell`, `invoices.view`, `invoices.issue`, `documents.view`, `documents.manage`, `documents.download_private`, `notifications.view`, `notifications.send`, `notifications.manage_templates`, `campaigns.view`, `campaigns.manage`, `campaigns.send`, `reports.view`, `imports.manage`, `data.export`, `leads.view`, `leads.manage`, `leads.assign`, `leads.export`, `analytics.view`, `analytics.export`, `privacy.view`, `privacy.manage`, `privacy.export`, `help.view`.
- Funciones a probar: operación integral de su sede: vehículos, inventario, clientes, ventas, facturación, documentos, CRM, campañas, reportes, imports, analítica y privacidad.

La fuente de verdad es [la matriz de permisos](../auditoria-integral/04-matriz-rbac.md) (RBAC significa control de acceso según el rol); un permiso sólo es efectivo con cuenta, rol, asignación y módulo activos.

## Requisitos previos

- Entorno local/QA/staging autorizado y commit registrado.
- Cuenta exclusiva para el rol, sin flags Django adicionales.
- Asignación vigente con el alcance indicado.
- Datos sintéticos; dos sucursales o expedientes cuando el caso exige aislamiento.
- Copia de [la plantilla de ejecución](testeo-plantilla-ejecucion.md).

## Casos

| ID | Caso | Precondiciones | Pasos numerados | Resultado esperado observable | Resultado obtenido | Estado | Evidencia | Observaciones |
|---|---|---|---|---|---|---|---|---|
| RAS-001 | Acceso y navegación | Cuenta activa con asignación vigente. | 1. Iniciar sesión. 2. Abrir el dashboard. 3. Recorrer sólo las entradas visibles del menú. 4. Volver con navegación del producto. | El perfil de dashboard corresponde al rol; no aparecen acciones ajenas y no hay errores técnicos. |  | pendiente |  |  |
| RAS-002 | Funciones permitidas | Datos sintéticos y módulos requeridos habilitados. | 1. Abrir las guías `VEH`, `INV`, `CP`, `CV`, `FD`, `PN`, `RAI` y `PA`. 2. Ejecutar un caso de lectura por cada área indicada. 3. Confirmar filtros y datos persistidos. | Las funciones visibles coinciden con: operación integral de su sede: vehículos, inventario, clientes, ventas, facturación, documentos, CRM, campañas, reportes, imports, analítica y privacidad. |  | pendiente |  |  |
| RAS-003 | Mutación principal | Entorno no productivo y registros creados para esta ejecución. | 1. Registrar estado inicial. 2. Crear un cliente sintético y recorrer cotización → reserva → venta → comprobante dentro de su sucursal. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | La respuesta es controlada, la persistencia coincide con la acción y la auditoría existe cuando aplica. |  | pendiente |  |  |
| RAS-004 | Denegación por permiso o estado | URL objetivo conocida sin alterar el rol. | 1. Registrar estado inicial. 2. Abrir el centro empresarial o gestión global de seguridad por URL directa. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | Acceso denegado; el recurso ajeno no revela datos y normalmente responde 404. |  | pendiente |  |  |
| RAS-005 | Alcance y acceso horizontal | Dos sucursales o dos expedientes con datos distinguibles. | 1. Registrar estado inicial. 2. Intentar leer y mutar el mismo tipo de recurso en una segunda sucursal. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | La respuesta respeta el alcance descrito; no mezcla listados, exports, archivos ni mutaciones. |  | pendiente |  |  |
| RAS-006 | Sesión, ayuda y responsive | Navegador de escritorio y viewport móvil. | 1. Abrir ayuda contextual. 2. Repetir dashboard y una lista a 360 px y escritorio. 3. Cerrar sesión por la acción POST. 4. Usar Atrás y reabrir una URL privada. | Controles utilizables sin solapamiento; ayuda corresponde al rol; tras logout no reaparece contenido privado. |  | pendiente |  |  |

## Checklist

- [ ] `RAS-001` ejecutado y documentado.
- [ ] `RAS-002` ejecutado y documentado.
- [ ] `RAS-003` ejecutado y documentado.
- [ ] `RAS-004` ejecutado y documentado.
- [ ] `RAS-005` ejecutado y documentado.
- [ ] `RAS-006` ejecutado y documentado.
- [ ] No se modificaron permisos para obtener un resultado favorable.
- [ ] Evidencia redactada y sin secretos.

## Incidencias y conformidad

- Incidencias relacionadas:
- Observaciones del rol:
- Conformidad: `conforme` / `con reservas` / `no conforme`.
- Evaluador y fecha: completar en la ficha separada.
