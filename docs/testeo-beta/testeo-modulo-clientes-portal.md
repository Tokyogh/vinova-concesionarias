# Testeo beta — módulo Clientes y portal

## Objetivo

Validar expedientes, asociación cuenta-cliente, portal e intentos de abrir datos de otro cliente.

## Roles y permisos

Personal con `customers.view/manage`; cuenta `cliente` con `portal.access`.

## Requisitos previos

- Dos clientes, dos cuentas cliente, dos sucursales y datos sintéticos de vehículo/factura/documento.
- Entorno y commit registrados en la plantilla individual.
- Datos sintéticos identificables y evidencia sin secretos.

## Casos

| ID | Módulo | Precondiciones | Pasos numerados | Resultado esperado observable | Resultado obtenido | Estado | Evidencia | Observaciones |
|---|---|---|---|---|---|---|---|---|
| CP-001 | Crear expediente | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Crear persona natural y empresa con identificaciones sintéticas válidas. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Tipo, identificación y nombre/razón social se validan y el expediente queda en la sede elegida. |  | pendiente |  |  |
| CP-002 | Duplicados y normalización | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Repetir identificación con formato equivalente y probar valores inválidos. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Se normaliza y rechaza el duplicado/valor inválido sin expediente adicional. |  | pendiente |  |  |
| CP-003 | Editar, notas e intereses | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Actualizar contacto y añadir nota/interés mediante la interfaz autorizada. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Los cambios persisten con autor/fecha y respetan sucursal. |  | pendiente |  |  |
| CP-004 | Vinculación legítima | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Seleccionar explícitamente cuenta y expediente sin asociación y ejecutar el servicio/UI autorizado. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | La relación uno-a-uno queda auditable; contraseña y permisos no cambian implícitamente. |  | pendiente |  |  |
| CP-005 | Asociación ambigua o ocupada | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Intentar vincular cuenta/expediente ya usados o basarse sólo en coincidencia textual. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | La operación se detiene con error controlado y no cambia la cuenta propietaria del expediente. |  | pendiente |  |  |
| CP-006 | Cliente heredado vinculado | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Iniciar sesión con una cuenta antigua que ya tiene relación válida. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Accede al dashboard sin crear Customer ni duplicar relación. |  | pendiente |  |  |
| CP-007 | Sin expediente o inactivo | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Entrar con `portal.access` sin Customer y luego con expediente inactivo/eliminado lógicamente. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Se muestra página segura de vinculación/activación, nunca 404 técnico ni traceback. |  | pendiente |  |  |
| CP-008 | Perfil y preferencias | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Editar contacto/preferencias permitidas desde el portal y recargar. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Sólo campos propios autorizados cambian; datos empresariales permanecen intactos. |  | pendiente |  |  |
| CP-009 | Datos de otro cliente | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Cambiar IDs/URLs para vehículo, factura, documento y notificación del segundo cliente. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Todos los intentos de abrir datos ajenos se deniegan sin revelar metadatos. |  | pendiente |  |  |
| CP-010 | Cliente contra staff | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Abrir `/dashboard/`; con staff sin `portal.access`, abrir `/mi-cuenta/`. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Cliente no entra al backoffice y staff no recibe privilegio de cliente implícito. |  | pendiente |  |  |

## Checklist

- [ ] `CP-001` ejecutado.
- [ ] `CP-002` ejecutado.
- [ ] `CP-003` ejecutado.
- [ ] `CP-004` ejecutado.
- [ ] `CP-005` ejecutado.
- [ ] `CP-006` ejecutado.
- [ ] `CP-007` ejecutado.
- [ ] `CP-008` ejecutado.
- [ ] `CP-009` ejecutado.
- [ ] `CP-010` ejecutado.
- [ ] Validaciones de servidor comprobadas, no sólo controles visuales.
- [ ] Aislamiento de datos propios y de otra persona o sucursal comprobado también por URL directa.
- [ ] Responsive revisado en la pantalla principal.

## Integraciones, bloqueos y conformidad

Nunca vincular sólo por correo, cédula o nombre; usar el servicio legítimo y no crear duplicados.

- Incidencias:
- Bloqueos externos:
- Observaciones:
- Conformidad: `conforme` / `con reservas` / `no conforme`.
