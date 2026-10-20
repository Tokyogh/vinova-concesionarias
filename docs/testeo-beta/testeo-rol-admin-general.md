# Testeo beta — rol Administración general

## Objetivo

Validar manualmente el contrato del rol `admin_general` sin ampliar privilegios ni alcance.

## Rol, permisos y alcance

- Código: `admin_general`.
- Alcance esperado: Global.
- Permisos: Los 63 `PermissionCode` vigentes de la matriz canónica.
- Funciones a probar: administración empresarial y de todos los dominios operativos; incluir acceso Staff, consentimiento, sedes enriquecidas y repuestos públicos; SRI operativo sigue excluido.

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
| RAG-001 | Acceso y navegación | Cuenta activa con asignación vigente. | 1. Iniciar sesión. 2. Abrir el dashboard. 3. Recorrer sólo las entradas visibles del menú. 4. Volver con navegación del producto. | El perfil de dashboard corresponde al rol; no aparecen acciones ajenas y no hay errores técnicos. |  | pendiente |  |  |
| RAG-002 | Funciones permitidas | Datos sintéticos y módulos requeridos habilitados. | 1. Abrir todas las guías modulares dentro del producto habilitado. 2. Ejecutar un caso de lectura por cada área indicada. 3. Confirmar filtros y datos persistidos. | Las funciones visibles coinciden con: administración empresarial y de todos los dominios operativos; SRI operativo sigue excluido. |  | pendiente |  |  |
| RAG-003 | Mutación principal | Entorno no productivo y registros creados para esta ejecución. | 1. Registrar estado inicial. 2. Gestionar una sucursal sintética, un usuario y una configuración modular; comprobar persistencia y auditoría. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | La respuesta es controlada, la persistencia coincide con la acción y la auditoría existe cuando aplica. |  | pendiente |  |  |
| RAG-004 | Denegación por permiso o estado | URL objetivo conocida sin alterar el rol. | 1. Registrar estado inicial. 2. Deshabilitar un módulo y abrir su URL directa conservando el permiso. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | El interruptor del módulo prevalece y la ruta no expone la función deshabilitada. |  | pendiente |  |  |
| RAG-005 | Alcance y acceso horizontal | Dos sucursales o dos expedientes con datos distinguibles. | 1. Registrar estado inicial. 2. Consultar y editar recursos sintéticos de dos sucursales, confirmando que cada cambio conserva su sede. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | La respuesta respeta el alcance descrito; no mezcla listados, exports, archivos ni mutaciones. |  | pendiente |  |  |
| RAG-006 | Sesión, ayuda y responsive | Navegador de escritorio y viewport móvil. | 1. Abrir ayuda contextual. 2. Repetir dashboard y una lista a 360 px y escritorio. 3. Cerrar sesión por la acción POST. 4. Usar Atrás y reabrir una URL privada. | Controles utilizables sin solapamiento; ayuda corresponde al rol; tras logout no reaparece contenido privado. |  | pendiente |  |  |

## Checklist

- [ ] `RAG-001` ejecutado y documentado.
- [ ] `RAG-002` ejecutado y documentado.
- [ ] `RAG-003` ejecutado y documentado.
- [ ] `RAG-004` ejecutado y documentado.
- [ ] `RAG-005` ejecutado y documentado.
- [ ] `RAG-006` ejecutado y documentado.
- [ ] No se modificaron permisos para obtener un resultado favorable.
- [ ] Evidencia redactada y sin secretos.

## Incidencias y conformidad

- Incidencias relacionadas:
- Observaciones del rol:
- Conformidad: `conforme` / `con reservas` / `no conforme`.
- Evaluador y fecha: completar en la ficha separada.
