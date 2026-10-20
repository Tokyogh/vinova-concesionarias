# Testeo beta — módulo Facturación y documentos

## Objetivo

Validar comprobantes internos, pagos, anulaciones, PDF y archivos privados.

## Roles y permisos

`invoices.view/issue/manage/void`, `documents.view/manage/download_private` según rol y sede.

## Requisitos previos

- Venta sintética confirmable, dos clientes/sucursales y almacenamiento de pruebas.
- Entorno y commit registrados en la plantilla individual.
- Datos sintéticos identificables y evidencia sin secretos.

## Casos

| ID | Módulo | Precondiciones | Pasos numerados | Resultado esperado observable | Resultado obtenido | Estado | Evidencia | Observaciones |
|---|---|---|---|---|---|---|---|---|
| FD-001 | Crear desde venta | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Generar comprobante desde una venta elegible. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Cliente, sede, líneas y totales se copian una vez sin duplicar. |  | pendiente |  |  |
| FD-002 | Emitir | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Emitir borrador con numeración válida. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Estado/número/fecha persisten y una reemisión inválida se bloquea. |  | pendiente |  |  |
| FD-003 | Registrar pago | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Añadir pago menor/igual al saldo y recargar. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Pagado/saldo se recalculan en servidor con precisión decimal. |  | pendiente |  |  |
| FD-004 | Anular pago | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Anular pago sintético con motivo. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Saldo revierte y el registro conserva historial. |  | pendiente |  |  |
| FD-005 | Anular factura | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Anular comprobante elegible con permiso y motivo. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Estado anulado persiste; no se borra ni aparece como vigente. |  | pendiente |  |  |
| FD-006 | PDF | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Generar/descargar PDF y comparar número, cliente, líneas y total. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | PDF válido coincide con datos y no incluye secretos internos. |  | pendiente |  |  |
| FD-007 | Portal de factura | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Abrir la factura con su cliente propietario. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Se visualiza/descarga sólo información del expediente propio. |  | pendiente |  |  |
| FD-008 | Factura de otro cliente | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Cambiar ID por factura de otro cliente/sucursal. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Respuesta controlada sin contenido, PDF ni auditoría falsa de éxito. |  | pendiente |  |  |
| FD-009 | Crear documento privado | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Cargar archivo permitido asociado a cliente/vehículo/venta. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Metadatos, hash, relación con el titular y almacenamiento privado quedan correctos. |  | pendiente |  |  |
| FD-010 | Descarga auditada | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Descargar con permiso y revisar evento. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Sólo autorizado recibe archivo y la descarga exitosa queda auditada. |  | pendiente |  |  |
| FD-011 | Archivo inválido | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Subir extensión/MIME/contenido prohibido, nombre traversal o tamaño fuera de límite. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Validación server-side rechaza y no deja blob ni registro parcial. |  | pendiente |  |  |
| FD-012 | Lifecycle documental | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Reemplazar/retirar un documento sintético y probar recurso ajeno. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Versionado/estado se conserva; el ajeno no se lee ni modifica. |  | pendiente |  |  |

## Checklist

- [ ] `FD-001` ejecutado.
- [ ] `FD-002` ejecutado.
- [ ] `FD-003` ejecutado.
- [ ] `FD-004` ejecutado.
- [ ] `FD-005` ejecutado.
- [ ] `FD-006` ejecutado.
- [ ] `FD-007` ejecutado.
- [ ] `FD-008` ejecutado.
- [ ] `FD-009` ejecutado.
- [ ] `FD-010` ejecutado.
- [ ] `FD-011` ejecutado.
- [ ] `FD-012` ejecutado.
- [ ] Validaciones de servidor comprobadas, no sólo controles visuales.
- [ ] Aislamiento de datos propios y de otra persona o sucursal comprobado también por URL directa.
- [ ] Responsive revisado en la pantalla principal.

## Integraciones, bloqueos y conformidad

La factura interna no equivale a SRI; no probar firma/envío fiscal.

- Incidencias:
- Bloqueos externos:
- Observaciones:
- Conformidad: `conforme` / `con reservas` / `no conforme`.
