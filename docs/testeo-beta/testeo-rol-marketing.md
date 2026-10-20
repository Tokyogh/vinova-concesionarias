# Testeo beta — rol Marketing

## Objetivo

Validar manualmente el contrato del rol `marketing` sin ampliar privilegios ni alcance.

## Rol, permisos y alcance

- Código: `marketing`.
- Alcance esperado: Global o sucursal asignada explícitamente.
- Permisos: `dashboard.view`, `vehicles.view`, `vehicles.manage`, `vehicles.publish`, `customers.view`, `notifications.view`, `notifications.send`, `notifications.manage_templates`, `campaigns.view`, `campaigns.manage`, `campaigns.send`, `imports.manage`, `analytics.view`, `help.view`.
- Funciones a probar: contenido/publicación vehicular, segmentos, plantillas, campañas con consentimiento, importaciones, analítica consentida y revisión pública de repuestos.

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
| RMK-001 | Acceso y navegación | Cuenta activa con asignación vigente. | 1. Iniciar sesión. 2. Abrir el dashboard. 3. Recorrer sólo las entradas visibles del menú. 4. Volver con navegación del producto. | El perfil de dashboard corresponde al rol; no aparecen acciones ajenas y no hay errores técnicos. |  | pendiente |  |  |
| RMK-002 | Funciones permitidas | Datos sintéticos y módulos requeridos habilitados. | 1. Abrir publicación en `VEH`, campañas en `PN` y analítica/importaciones en `RAI`. 2. Ejecutar un caso de lectura por cada área indicada. 3. Confirmar filtros y datos persistidos. | Las funciones visibles coinciden con: contenido/publicación vehicular, segmentos, plantillas, campañas con consentimiento, importaciones y analítica. |  | pendiente |  |  |
| RMK-003 | Mutación principal | Entorno no productivo y registros creados para esta ejecución. | 1. Registrar estado inicial. 2. Publicar un vehículo sintético completo y preparar una campaña; revisar destinatarios antes de confirmarla explícitamente. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | La respuesta es controlada, la persistencia coincide con la acción y la auditoría existe cuando aplica. |  | pendiente |  |  |
| RMK-004 | Denegación por permiso o estado | URL objetivo conocida sin alterar el rol. | 1. Registrar estado inicial. 2. Intentar vender, emitir factura o anonimizar un cliente. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | No se ejecuta la operación comercial/privacidad y no se filtran datos de otra sede. |  | pendiente |  |  |
| RMK-005 | Alcance y acceso horizontal | Dos sucursales o dos expedientes con datos distinguibles. | 1. Registrar estado inicial. 2. Con asignación de sede, confirmar que segmentos, vehículos y destinatarios no incorporan otra sucursal. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | La respuesta respeta el alcance descrito; no mezcla listados, exports, archivos ni mutaciones. |  | pendiente |  |  |
| RMK-006 | Sesión, ayuda y responsive | Navegador de escritorio y viewport móvil. | 1. Abrir ayuda contextual. 2. Repetir dashboard y una lista a 360 px y escritorio. 3. Cerrar sesión por la acción POST. 4. Usar Atrás y reabrir una URL privada. | Controles utilizables sin solapamiento; ayuda corresponde al rol; tras logout no reaparece contenido privado. |  | pendiente |  |  |

## Checklist

- [ ] `RMK-001` ejecutado y documentado.
- [ ] `RMK-002` ejecutado y documentado.
- [ ] `RMK-003` ejecutado y documentado.
- [ ] `RMK-004` ejecutado y documentado.
- [ ] `RMK-005` ejecutado y documentado.
- [ ] `RMK-006` ejecutado y documentado.
- [ ] No se modificaron permisos para obtener un resultado favorable.
- [ ] Evidencia redactada y sin secretos.

## Incidencias y conformidad

- Incidencias relacionadas:
- Observaciones del rol:
- Conformidad: `conforme` / `con reservas` / `no conforme`.
- Evaluador y fecha: completar en la ficha separada.
