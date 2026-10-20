# Testeo beta — rol Jefatura de inventario

## Objetivo

Validar manualmente el contrato del rol `jefe_inventario` sin ampliar privilegios ni alcance.

## Rol, permisos y alcance

- Código: `jefe_inventario`.
- Alcance esperado: Sucursal obligatoria.
- Permisos: `dashboard.view`, `vehicles.view`, `vehicles.manage`, `inventory.view`, `inventory.manage_stock`, `reports.view`, `imports.manage`, `data.export`, `help.view`.
- Funciones a probar: vehículos, artículos, stock, movimientos, transferencias, importaciones, exportes y publicación segura de repuestos de su sede.

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
| RJI-001 | Acceso y navegación | Cuenta activa con asignación vigente. | 1. Iniciar sesión. 2. Abrir el dashboard. 3. Recorrer sólo las entradas visibles del menú. 4. Volver con navegación del producto. | El perfil de dashboard corresponde al rol; no aparecen acciones ajenas y no hay errores técnicos. |  | pendiente |  |  |
| RJI-002 | Funciones permitidas | Datos sintéticos y módulos requeridos habilitados. | 1. Abrir las guías `VEH`, `INV` y casos aplicables de `RAI`. 2. Ejecutar un caso de lectura por cada área indicada. 3. Confirmar filtros y datos persistidos. | Las funciones visibles coinciden con: vehículos, artículos, stock, movimientos, transferencias, imports y exportes operativos de su sede. |  | pendiente |  |  |
| RJI-003 | Mutación principal | Entorno no productivo y registros creados para esta ejecución. | 1. Registrar estado inicial. 2. Registrar entrada, salida/ajuste y transferencia sintéticas; comprobar stock, mínimo, ubicación y trazabilidad. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | La respuesta es controlada, la persistencia coincide con la acción y la auditoría existe cuando aplica. |  | pendiente |  |  |
| RJI-004 | Denegación por permiso o estado | URL objetivo conocida sin alterar el rol. | 1. Registrar estado inicial. 2. Intentar abrir expedientes de clientes o emitir facturas. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | No se muestran datos ajenos ni se registra movimiento fuera del alcance. |  | pendiente |  |  |
| RJI-005 | Alcance y acceso horizontal | Dos sucursales o dos expedientes con datos distinguibles. | 1. Registrar estado inicial. 2. Intentar mover o editar stock perteneciente a otra sucursal. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | La respuesta respeta el alcance descrito; no mezcla listados, exports, archivos ni mutaciones. |  | pendiente |  |  |
| RJI-006 | Sesión, ayuda y responsive | Navegador de escritorio y viewport móvil. | 1. Abrir ayuda contextual. 2. Repetir dashboard y una lista a 360 px y escritorio. 3. Cerrar sesión por la acción POST. 4. Usar Atrás y reabrir una URL privada. | Controles utilizables sin solapamiento; ayuda corresponde al rol; tras logout no reaparece contenido privado. |  | pendiente |  |  |

## Checklist

- [ ] `RJI-001` ejecutado y documentado.
- [ ] `RJI-002` ejecutado y documentado.
- [ ] `RJI-003` ejecutado y documentado.
- [ ] `RJI-004` ejecutado y documentado.
- [ ] `RJI-005` ejecutado y documentado.
- [ ] `RJI-006` ejecutado y documentado.
- [ ] No se modificaron permisos para obtener un resultado favorable.
- [ ] Evidencia redactada y sin secretos.

## Incidencias y conformidad

- Incidencias relacionadas:
- Observaciones del rol:
- Conformidad: `conforme` / `con reservas` / `no conforme`.
- Evaluador y fecha: completar en la ficha separada.
