# Testeo beta — rol Asesoría de postventa

## Objetivo

Validar manualmente el contrato del rol `asesor_postventa` sin ampliar privilegios ni alcance.

## Rol, permisos y alcance

- Código: `asesor_postventa`.
- Alcance esperado: Sucursal obligatoria.
- Permisos: `dashboard.view`, `customers.view`, `vehicles.link_codes`, `documents.view`, `documents.download_private`, `notifications.view`, `notifications.send`, `post_sales.view`, `post_sales.manage`, `help.view`.
- Funciones a probar: consulta de clientes/documentos, códigos de vinculación, órdenes de servicio, historial y comunicación.

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
| RAP-001 | Acceso y navegación | Cuenta activa con asignación vigente. | 1. Iniciar sesión. 2. Abrir el dashboard. 3. Recorrer sólo las entradas visibles del menú. 4. Volver con navegación del producto. | El perfil de dashboard corresponde al rol; no aparecen acciones ajenas y no hay errores técnicos. |  | pendiente |  |  |
| RAP-002 | Funciones permitidas | Datos sintéticos y módulos requeridos habilitados. | 1. Abrir los casos de códigos en `VEH`, lectura de `CP`/`FD` y comunicación en `PN`. 2. Ejecutar un caso de lectura por cada área indicada. 3. Confirmar filtros y datos persistidos. | Las funciones visibles coinciden con: consulta de clientes/documentos, códigos de vinculación, órdenes de servicio, historial y comunicación. |  | pendiente |  |  |
| RAP-003 | Mutación principal | Entorno no productivo y registros creados para esta ejecución. | 1. Registrar estado inicial. 2. Con postventa ON, crear una orden sintética, avanzar sólo por estados válidos y comprobar historial del cliente. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | La respuesta es controlada, la persistencia coincide con la acción y la auditoría existe cuando aplica. |  | pendiente |  |  |
| RAP-004 | Denegación por permiso o estado | URL objetivo conocida sin alterar el rol. | 1. Registrar estado inicial. 2. Intentar editar cliente, vender vehículo o gestionar inventario. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | El backend deniega el recurso ajeno; postventa OFF oculta y bloquea la ruta aunque exista permiso. |  | pendiente |  |  |
| RAP-005 | Alcance y acceso horizontal | Dos sucursales o dos expedientes con datos distinguibles. | 1. Registrar estado inicial. 2. Intentar acceder a orden/documento de otra sucursal y a vehículo de otro cliente. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | La respuesta respeta el alcance descrito; no mezcla listados, exports, archivos ni mutaciones. |  | pendiente |  |  |
| RAP-006 | Sesión, ayuda y responsive | Navegador de escritorio y viewport móvil. | 1. Abrir ayuda contextual. 2. Repetir dashboard y una lista a 360 px y escritorio. 3. Cerrar sesión por la acción POST. 4. Usar Atrás y reabrir una URL privada. | Controles utilizables sin solapamiento; ayuda corresponde al rol; tras logout no reaparece contenido privado. |  | pendiente |  |  |

## Checklist

- [ ] `RAP-001` ejecutado y documentado.
- [ ] `RAP-002` ejecutado y documentado.
- [ ] `RAP-003` ejecutado y documentado.
- [ ] `RAP-004` ejecutado y documentado.
- [ ] `RAP-005` ejecutado y documentado.
- [ ] `RAP-006` ejecutado y documentado.
- [ ] No se modificaron permisos para obtener un resultado favorable.
- [ ] Evidencia redactada y sin secretos.

## Incidencias y conformidad

- Incidencias relacionadas:
- Observaciones del rol:
- Conformidad: `conforme` / `con reservas` / `no conforme`.
- Evaluador y fecha: completar en la ficha separada.
