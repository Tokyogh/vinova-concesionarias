# Testeo beta — rol Cliente

## Objetivo

Validar manualmente el contrato del rol `cliente` sin ampliar privilegios ni alcance.

## Rol, permisos y alcance

- Código: `cliente`.
- Alcance esperado: acceso exclusivo al expediente vinculado a su cuenta mediante `Customer.account` y permiso `portal.access`.
- Permisos: `portal.access`.
- Funciones a probar: dashboard privado, perfil/preferencias, elección de cookies, garaje, vehículos propios, documentos, facturas, notificaciones y postventa cuando está habilitada.

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
| RCL-001 | Acceso y navegación | Cuenta activa con asignación vigente. | 1. Iniciar sesión. 2. Abrir el dashboard. 3. Recorrer sólo las entradas visibles del menú. 4. Volver con navegación del producto. | El perfil de dashboard corresponde al rol; no aparecen acciones ajenas y no hay errores técnicos. |  | pendiente |  |  |
| RCL-002 | Funciones permitidas | Datos sintéticos y módulos requeridos habilitados. | 1. Abrir los casos de datos propios en `CP`, garaje/código en `VEH` y portal en `FD`/`PN`. 2. Ejecutar un caso de lectura por cada área indicada. 3. Confirmar filtros y datos persistidos. | Las funciones visibles coinciden con: dashboard privado, perfil/preferencias, garaje, vehículos propios, documentos, facturas, notificaciones y postventa cuando está habilitada. |  | pendiente |  |  |
| RCL-003 | Mutación principal | Entorno no productivo y registros creados para esta ejecución. | 1. Registrar estado inicial. 2. Recorrer dashboard, perfil, vehículo propio, factura, documento y notificación; modificar sólo preferencias propias. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | La respuesta es controlada, la persistencia coincide con la acción y la auditoría existe cuando aplica. |  | pendiente |  |  |
| RCL-004 | Denegación por permiso o estado | URL objetivo conocida sin alterar el rol. | 1. Registrar estado inicial. 2. Abrir `/dashboard/` y URLs/identificadores pertenecientes a otro cliente. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | No existe acceso horizontal; el cliente sin expediente recibe respuesta controlada y nunca traceback. |  | pendiente |  |  |
| RCL-005 | Alcance y acceso horizontal | Dos sucursales o dos expedientes con datos distinguibles. | 1. Registrar estado inicial. 2. Preparar dos cuentas con dos expedientes y cruzar vehículos, documentos, facturas y mensajes. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | La respuesta respeta el alcance descrito; no mezcla listados, exports, archivos ni mutaciones. |  | pendiente |  |  |
| RCL-006 | Sesión, ayuda y responsive | Navegador de escritorio y viewport móvil. | 1. Abrir ayuda contextual. 2. Repetir dashboard y una lista a 360 px y escritorio. 3. Cerrar sesión por la acción POST. 4. Usar Atrás y reabrir una URL privada. | Controles utilizables sin solapamiento; ayuda corresponde al rol; tras logout no reaparece contenido privado. |  | pendiente |  |  |

## Checklist

- [ ] `RCL-001` ejecutado y documentado.
- [ ] `RCL-002` ejecutado y documentado.
- [ ] `RCL-003` ejecutado y documentado.
- [ ] `RCL-004` ejecutado y documentado.
- [ ] `RCL-005` ejecutado y documentado.
- [ ] `RCL-006` ejecutado y documentado.
- [ ] No se modificaron permisos para obtener un resultado favorable.
- [ ] Evidencia redactada y sin secretos.

## Incidencias y conformidad

- Incidencias relacionadas:
- Observaciones del rol:
- Conformidad: `conforme` / `con reservas` / `no conforme`.
- Evaluador y fecha: completar en la ficha separada.
