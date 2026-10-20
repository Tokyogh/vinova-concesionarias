# Testeo beta — módulo Vehículos

## Objetivo

Validar inventario vehicular, publicación, multimedia, catálogo, códigos y garaje.

## Roles y permisos

Lectura `vehicles.view`; gestión/publicación/códigos según `vehicles.manage`, `vehicles.publish`, `vehicles.link_codes`; cliente limitado a sus propios datos.

## Requisitos previos

- Marca/modelo, dos sucursales, personal autorizado y dos clientes sintéticos.
- Entorno y commit registrados en la plantilla individual.
- Datos sintéticos identificables y evidencia sin secretos.

## Casos

| ID | Módulo | Precondiciones | Pasos numerados | Resultado esperado observable | Resultado obtenido | Estado | Evidencia | Observaciones |
|---|---|---|---|---|---|---|---|---|
| VEH-001 | Marca, modelo y alta | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Crear marca/modelo y vehículo sintético con VIN/código/placa válidos. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Relaciones y campos persisten; no se duplica VIN/código único. |  | pendiente |  |  |
| VEH-002 | Validación y duplicados | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Enviar año/rangos inválidos y repetir VIN, código o slug. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | El servidor rechaza la entrada sin escritura parcial. |  | pendiente |  |  |
| VEH-003 | Publicar y retirar | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Completar ficha, publicar y luego retirar el mismo vehículo. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Publicado aparece en catálogo; retirado deja de aparecer sin borrarse internamente. |  | pendiente |  |  |
| VEH-004 | Catálogo y filtros | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Combinar marca/modelo/año/precio/búsqueda y limpiar filtros. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Tarjetas, conteo y URL corresponden; limpiar restaura catálogo disponible publicado. |  | pendiente |  |  |
| VEH-005 | Multimedia y ficha | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Subir archivo permitido, definir principal/alt y revisar galería/modelo alternativo. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Archivo válido se muestra; fallback neutral aparece cuando no existe recurso. |  | pendiente |  |  |
| VEH-006 | Código de vinculación | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Generar código, canjearlo una vez con cliente legítimo y reintentar. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | El primer canje crea vínculo auditable; el reuso/otro cliente se rechaza. |  | pendiente |  |  |
| VEH-007 | Garaje y datos propios | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Abrir vehículo propio y cambiar el ID por uno de otro cliente. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | El propio muestra datos permitidos; el ajeno responde controladamente sin filtración. |  | pendiente |  |  |
| VEH-008 | Estados comerciales | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Recorrer disponible → reservado → vendido mediante servicios de venta y probar transición inválida. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Sólo transiciones válidas persisten y catálogo/stock comercial reflejan el estado. |  | pendiente |  |  |
| VEH-009 | Sucursal y borrado | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Intentar editar recurso de otra sede y eliminación permanente sin/con permiso. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | La sede ajena y falta de permiso se deniegan; la prueba destructiva autorizada usa sólo registro desechable. |  | pendiente |  |  |

## Checklist

- [ ] `VEH-001` ejecutado.
- [ ] `VEH-002` ejecutado.
- [ ] `VEH-003` ejecutado.
- [ ] `VEH-004` ejecutado.
- [ ] `VEH-005` ejecutado.
- [ ] `VEH-006` ejecutado.
- [ ] `VEH-007` ejecutado.
- [ ] `VEH-008` ejecutado.
- [ ] `VEH-009` ejecutado.
- [ ] Validaciones de servidor comprobadas, no sólo controles visuales.
- [ ] Aislamiento de datos propios y de otra persona o sucursal comprobado también por URL directa.
- [ ] Responsive revisado en la pantalla principal.

## Integraciones, bloqueos y conformidad

No usar VIN/placas reales; la eliminación permanente sólo se prueba en entorno desechable y con permiso explícito.

- Incidencias:
- Bloqueos externos:
- Observaciones:
- Conformidad: `conforme` / `con reservas` / `no conforme`.
