# Testeo beta — módulo Postventa y notificaciones

## Objetivo

Validar interruptor del módulo de postventa, órdenes, mensajes, plantillas, preferencias y campañas consentidas.

## Roles y permisos

`post_sales.view/manage`, `notifications.view/send/manage_templates`, `campaigns.view/manage/send` y acceso del cliente únicamente a sus datos.

## Requisitos previos

- Dos sucursales/clientes, vehículo vinculado y módulo postventa controlable.
- Entorno y commit registrados en la plantilla individual.
- Datos sintéticos identificables y evidencia sin secretos.

## Casos

| ID | Módulo | Precondiciones | Pasos numerados | Resultado esperado observable | Resultado obtenido | Estado | Evidencia | Observaciones |
|---|---|---|---|---|---|---|---|---|
| PN-001 | Postventa OFF | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Deshabilitar módulo y abrir menú/URL con permiso. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Navegación desaparece y URL queda bloqueada sin quitar otros permisos. |  | pendiente |  |  |
| PN-002 | Crear orden | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Habilitar módulo y crear orden para vehículo/cliente propios. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Orden conserva sede, vehículo, descripción y estado inicial. |  | pendiente |  |  |
| PN-003 | Transiciones | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Avanzar por estados válidos y forzar salto inválido. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Sólo secuencia válida persiste y queda auditada. |  | pendiente |  |  |
| PN-004 | Líneas y próximo servicio | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Añadir trabajo/repuesto/kilometraje/fecha permitidos. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Totales/historial se muestran; no se crea recordatorio automático excluido. |  | pendiente |  |  |
| PN-005 | Portal postventa | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Abrir orden propia y luego cambiar ID por otra. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | La propia aparece cuando módulo ON; la ajena se deniega. |  | pendiente |  |  |
| PN-006 | Enviar notificación | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Seleccionar destinatarios internos/clientes autorizados y enviar mensaje sintético. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Se crean mensaje/recipientes correctos sin incluir otra sede. |  | pendiente |  |  |
| PN-007 | Bandeja y lectura | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Abrir inbox/detalle y marcar leído como destinatario. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Estado cambia sólo para ese destinatario; tercero no puede marcarlo. |  | pendiente |  |  |
| PN-008 | Preferencias | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Desactivar canal/categoría permitida desde cuenta cliente. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Preferencia persiste y el servicio la respeta. |  | pendiente |  |  |
| PN-009 | Plantilla | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Crear/editar plantilla con variables permitidas y probar variable insegura. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Variables válidas renderizan; desconocidas/inseguras se rechazan. |  | pendiente |  |  |
| PN-010 | Segmento de campaña | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Calcular segmento por actividad/compra/marca con consentimiento. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Snapshot contiene sólo clientes elegibles, vigentes y del alcance. |  | pendiente |  |  |
| PN-011 | Preparar vista previa | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Congelar destinatarios y preparar asunto/cuerpo. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Vista previa usa snapshot y no envía al abrir GET. |  | pendiente |  |  |
| PN-012 | Confirmar campaña | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Confirmar una vez con permiso `campaigns.send` y repetir. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Primera confirmación registra envío interno; repetición es idempotente. |  | pendiente |  |  |
| PN-013 | Consentimiento revocado y scope | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Revocar consentimiento antes de confirmar e intentar campaña ajena. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Se revalida, excluye/cancela según resultado y deniega otra sucursal. |  | pendiente |  |  |

## Checklist

- [ ] `PN-001` ejecutado.
- [ ] `PN-002` ejecutado.
- [ ] `PN-003` ejecutado.
- [ ] `PN-004` ejecutado.
- [ ] `PN-005` ejecutado.
- [ ] `PN-006` ejecutado.
- [ ] `PN-007` ejecutado.
- [ ] `PN-008` ejecutado.
- [ ] `PN-009` ejecutado.
- [ ] `PN-010` ejecutado.
- [ ] `PN-011` ejecutado.
- [ ] `PN-012` ejecutado.
- [ ] `PN-013` ejecutado.
- [ ] Validaciones de servidor comprobadas, no sólo controles visuales.
- [ ] Aislamiento de datos propios y de otra persona o sucursal comprobado también por URL directa.
- [ ] Responsive revisado en la pantalla principal.

## Integraciones, bloqueos y conformidad

No enviar proveedores reales; campañas requieren confirmación explícita y consentimiento vigente.

- Incidencias:
- Bloqueos externos:
- Observaciones:
- Conformidad: `conforme` / `con reservas` / `no conforme`.
