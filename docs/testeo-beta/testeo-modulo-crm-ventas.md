# Testeo beta — módulo CRM, leads y ventas

## Objetivo

Validar captación, pipeline, actividades, cotización, reserva, venta, pagos y anulaciones.

## Roles y permisos

`leads.*`, `sales.quote`, `sales.reserve`, `sales.sell` según rol y sucursal.

## Requisitos previos

- Dos sucursales, cliente/vehículo sintéticos y usuarios comerciales con permisos diferenciados.
- Entorno y commit registrados en la plantilla individual.
- Datos sintéticos identificables y evidencia sin secretos.

## Casos

| ID | Módulo | Precondiciones | Pasos numerados | Resultado esperado observable | Resultado obtenido | Estado | Evidencia | Observaciones |
|---|---|---|---|---|---|---|---|---|
| CV-001 | Lead público válido | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Enviar formulario público con consentimiento y datos sintéticos. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Se crea un lead una sola vez con fuente/fecha correctas y respuesta pública segura. |  | pendiente |  |  |
| CV-002 | Lead inválido y abuso | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Omitir consentimiento, usar formatos inválidos y repetir rápidamente. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Validación/rate limit rechazan sin revelar internals ni crear basura. |  | pendiente |  |  |
| CV-003 | Pipeline y filtros | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Cambiar estado permitido y filtrar por etapa, responsable, fecha y sede. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | El tablero refleja estado persistido y no mezcla otra sucursal. |  | pendiente |  |  |
| CV-004 | Asignación y actividad | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Asignar lead autorizado y registrar llamada/nota/seguimiento. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Asignación y actividad conservan actor, fecha y contenido validado. |  | pendiente |  |  |
| CV-005 | Test drive | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Programar con vehículo/fecha válidos y probar conflicto o dato inválido. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | La cita válida persiste; conflicto/inválido se rechaza sin duplicar. |  | pendiente |  |  |
| CV-006 | Cotización | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Crear líneas, descuentos/impuestos permitidos y recalcular. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Subtotal, descuento, impuesto y total son coherentes y server-side. |  | pendiente |  |  |
| CV-007 | Reserva | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Reservar vehículo disponible con vencimiento válido. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Venta/vehículo pasan a reservado bajo lock; una segunda reserva no gana carrera. |  | pendiente |  |  |
| CV-008 | Vencimiento o liberación | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Liberar/cancelar una reserva sintética según flujo. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Estado vuelve al permitido y queda trazabilidad; no borra la operación. |  | pendiente |  |  |
| CV-009 | Confirmar venta | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Confirmar venta elegible con rol `sales.sell`. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Cliente, vehículo, líneas y estado se actualizan atómicamente. |  | pendiente |  |  |
| CV-010 | Pago y anulación | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Registrar pago sintético y anularlo con motivo autorizado. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Saldos se recalculan y la anulación conserva historial. |  | pendiente |  |  |
| CV-011 | Aprobación/estado inválido | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Forzar transición o condición que requiere aprobación. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | El servicio bloquea o enruta según política; no salta controles desde URL. |  | pendiente |  |  |
| CV-012 | Alcance y permisos | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Abrir/mutar lead, cotización o venta de otra sede y probar vendedor sin `sales.sell`. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | El recurso ajeno/no permitido se deniega sin cambiar estado ni exportarlo. |  | pendiente |  |  |

## Checklist

- [ ] `CV-001` ejecutado.
- [ ] `CV-002` ejecutado.
- [ ] `CV-003` ejecutado.
- [ ] `CV-004` ejecutado.
- [ ] `CV-005` ejecutado.
- [ ] `CV-006` ejecutado.
- [ ] `CV-007` ejecutado.
- [ ] `CV-008` ejecutado.
- [ ] `CV-009` ejecutado.
- [ ] `CV-010` ejecutado.
- [ ] `CV-011` ejecutado.
- [ ] `CV-012` ejecutado.
- [ ] Validaciones de servidor comprobadas, no sólo controles visuales.
- [ ] Aislamiento de datos propios y de otra persona o sucursal comprobado también por URL directa.
- [ ] Responsive revisado en la pantalla principal.

## Integraciones, bloqueos y conformidad

No contactar personas reales ni ejecutar pagos externos.

- Incidencias:
- Bloqueos externos:
- Observaciones:
- Conformidad: `conforme` / `con reservas` / `no conforme`.
