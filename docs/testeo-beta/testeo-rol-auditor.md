# Testeo beta — rol Auditoría

## Objetivo

Validar manualmente el contrato del rol `auditor` sin ampliar privilegios ni alcance.

## Rol, permisos y alcance

- Código: `auditor`.
- Alcance esperado: Global o sucursal asignada; lectura salvo exportaciones expresamente autorizadas.
- Permisos: `dashboard.view`, `vehicles.view`, `inventory.view`, `customers.view`, `sales.quote`, `invoices.view`, `documents.view`, `notifications.view`, `reports.view`, `data.export`, `audit.view`, `audit.export`, `leads.view`, `leads.export`, `analytics.view`, `analytics.export`, `continuity.view`, `privacy.view`, `privacy.export`, `security.view`, `integrations.view`, `quality.view`, `help.view`.
- Funciones a probar: lectura transversal, reportes/exportes autorizados, auditoría, continuidad, privacidad, seguridad, integraciones y QA; incluir eventos de solicitudes/aprobaciones Staff sin revelar señales técnicas.

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
| RAU-001 | Acceso y navegación | Cuenta activa con asignación vigente. | 1. Iniciar sesión. 2. Abrir el dashboard. 3. Recorrer sólo las entradas visibles del menú. 4. Volver con navegación del producto. | El perfil de dashboard corresponde al rol; no aparecen acciones ajenas y no hay errores técnicos. |  | pendiente |  |  |
| RAU-002 | Funciones permitidas | Datos sintéticos y módulos requeridos habilitados. | 1. Abrir los casos de lectura y exportación de todas las guías, especialmente `RAI`, `PA`, `IC` y `QAC`. 2. Ejecutar un caso de lectura por cada área indicada. 3. Confirmar filtros y datos persistidos. | Las funciones visibles coinciden con: lectura transversal, reportes/exportes autorizados, auditoría, continuidad, privacidad, seguridad, integraciones y QA. |  | pendiente |  |  |
| RAU-003 | Mutación principal | Entorno no productivo y registros creados para esta ejecución. | 1. Registrar estado inicial. 2. Aplicar filtros y exportar un conjunto sintético autorizado; comparar conteos y alcance con la pantalla. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | La respuesta es controlada, la persistencia coincide con la acción y la auditoría existe cuando aplica. |  | pendiente |  |  |
| RAU-004 | Denegación por permiso o estado | URL objetivo conocida sin alterar el rol. | 1. Registrar estado inicial. 2. Enviar POST de edición sobre vehículo, stock, cliente, venta, factura o configuración. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | Toda mutación no permitida se deniega; no cambia la base ni se crea un evento de éxito. |  | pendiente |  |  |
| RAU-005 | Alcance y acceso horizontal | Dos sucursales o dos expedientes con datos distinguibles. | 1. Registrar estado inicial. 2. Con asignación de sede, comprobar que reportes y exports omiten la segunda sucursal. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | La respuesta respeta el alcance descrito; no mezcla listados, exports, archivos ni mutaciones. |  | pendiente |  |  |
| RAU-006 | Sesión, ayuda y responsive | Navegador de escritorio y viewport móvil. | 1. Abrir ayuda contextual. 2. Repetir dashboard y una lista a 360 px y escritorio. 3. Cerrar sesión por la acción POST. 4. Usar Atrás y reabrir una URL privada. | Controles utilizables sin solapamiento; ayuda corresponde al rol; tras logout no reaparece contenido privado. |  | pendiente |  |  |

## Checklist

- [ ] `RAU-001` ejecutado y documentado.
- [ ] `RAU-002` ejecutado y documentado.
- [ ] `RAU-003` ejecutado y documentado.
- [ ] `RAU-004` ejecutado y documentado.
- [ ] `RAU-005` ejecutado y documentado.
- [ ] `RAU-006` ejecutado y documentado.
- [ ] No se modificaron permisos para obtener un resultado favorable.
- [ ] Evidencia redactada y sin secretos.

## Incidencias y conformidad

- Incidencias relacionadas:
- Observaciones del rol:
- Conformidad: `conforme` / `con reservas` / `no conforme`.
- Evaluador y fecha: completar en la ficha separada.
