# Testeo beta — rol Bodega

## Objetivo

Validar manualmente el contrato del rol `bodega` sin ampliar privilegios ni alcance.

## Rol, permisos y alcance

- Código: `bodega`.
- Alcance esperado: Sucursal obligatoria.
- Permisos: `dashboard.view`, `inventory.view`, `inventory.manage_stock`, `help.view`.
- Funciones a probar: consulta de artículos, existencias, movimientos y operación de stock de su sede.

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
| RBO-001 | Acceso y navegación | Cuenta activa con asignación vigente. | 1. Iniciar sesión. 2. Abrir el dashboard. 3. Recorrer sólo las entradas visibles del menú. 4. Volver con navegación del producto. | El perfil de dashboard corresponde al rol; no aparecen acciones ajenas y no hay errores técnicos. |  | pendiente |  |  |
| RBO-002 | Funciones permitidas | Datos sintéticos y módulos requeridos habilitados. | 1. Abrir todos los casos aplicables de `INV`. 2. Ejecutar un caso de lectura por cada área indicada. 3. Confirmar filtros y datos persistidos. | Las funciones visibles coinciden con: consulta de artículos, existencias, movimientos y operación de stock de su sede. |  | pendiente |  |  |
| RBO-003 | Mutación principal | Entorno no productivo y registros creados para esta ejecución. | 1. Registrar estado inicial. 2. Registrar un movimiento sintético autorizado y comprobar cantidad resultante, referencia y usuario. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | La respuesta es controlada, la persistencia coincide con la acción y la auditoría existe cuando aplica. |  | pendiente |  |  |
| RBO-004 | Denegación por permiso o estado | URL objetivo conocida sin alterar el rol. | 1. Registrar estado inicial. 2. Intentar abrir clientes, ventas, facturas o editar vehículos. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | La operación ajena se deniega y ninguna existencia cambia. |  | pendiente |  |  |
| RBO-005 | Alcance y acceso horizontal | Dos sucursales o dos expedientes con datos distinguibles. | 1. Registrar estado inicial. 2. Intentar ajustar o transferir stock de una sede no asignada. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | La respuesta respeta el alcance descrito; no mezcla listados, exports, archivos ni mutaciones. |  | pendiente |  |  |
| RBO-006 | Sesión, ayuda y responsive | Navegador de escritorio y viewport móvil. | 1. Abrir ayuda contextual. 2. Repetir dashboard y una lista a 360 px y escritorio. 3. Cerrar sesión por la acción POST. 4. Usar Atrás y reabrir una URL privada. | Controles utilizables sin solapamiento; ayuda corresponde al rol; tras logout no reaparece contenido privado. |  | pendiente |  |  |

## Checklist

- [ ] `RBO-001` ejecutado y documentado.
- [ ] `RBO-002` ejecutado y documentado.
- [ ] `RBO-003` ejecutado y documentado.
- [ ] `RBO-004` ejecutado y documentado.
- [ ] `RBO-005` ejecutado y documentado.
- [ ] `RBO-006` ejecutado y documentado.
- [ ] No se modificaron permisos para obtener un resultado favorable.
- [ ] Evidencia redactada y sin secretos.

## Incidencias y conformidad

- Incidencias relacionadas:
- Observaciones del rol:
- Conformidad: `conforme` / `con reservas` / `no conforme`.
- Evaluador y fecha: completar en la ficha separada.
