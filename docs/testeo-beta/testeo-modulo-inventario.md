# Testeo beta — módulo Inventario y stock

## Objetivo

Validar artículos, existencias por sede, movimientos, transferencias y catálogo público de repuestos.

## Roles y permisos

`inventory.view` y `inventory.manage_stock`; alcance de sucursal obligatorio para roles operativos.

## Requisitos previos

- Dos sucursales, artículos/SKU sintéticos públicos y privados, imagen segura y existencias iniciales conocidas.
- Entorno y commit registrados en la plantilla individual.
- Datos sintéticos identificables y evidencia sin secretos.

## Casos

| ID | Módulo | Precondiciones | Pasos numerados | Resultado esperado observable | Resultado obtenido | Estado | Evidencia | Observaciones |
|---|---|---|---|---|---|---|---|---|
| INV-001 | Categoría y artículo | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Crear/editar categoría y artículo con SKU, descripción y estado. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Unicidad/formato se validan y el artículo queda reutilizable sin duplicados. |  | pendiente |  |  |
| INV-002 | Stock por sede | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Configurar cantidad, mínimo y ubicación para ambas sedes. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Cada sede conserva valores independientes y muestra alerta sólo cuando corresponde. |  | pendiente |  |  |
| INV-003 | Entrada | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Registrar entrada con cantidad y referencia válidas. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Aumenta exactamente el stock y se crea movimiento inmutable con actor/sede. |  | pendiente |  |  |
| INV-004 | Salida | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Registrar salida menor o igual a disponible. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Disminuye exactamente y nunca queda negativo. |  | pendiente |  |  |
| INV-005 | Ajuste | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Aplicar ajuste justificado sobre dato sintético. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Cantidad final coincide con el ajuste y conserva razón/referencia. |  | pendiente |  |  |
| INV-006 | Transferencia | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Transferir entre sedes con existencias suficientes. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Origen y destino cambian atómicamente y quedan movimientos enlazados. |  | pendiente |  |  |
| INV-007 | Insuficiencia y concurrencia | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Intentar salida/transferencias simultáneas que exceden disponible. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Una operación se rechaza; locks/constraints impiden saldo negativo o doble consumo. |  | pendiente |  |  |
| INV-008 | Filtros, mínimos y reporte | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Buscar por SKU/nombre, abrir bajo stock y comparar reporte/export. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Resultados y totales respetan filtros y sede. |  | pendiente |  |  |
| INV-009 | Alcance de sucursal | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Modificar stock de segunda sede con rol limitado y por URL directa. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Acceso denegado; no cambia ninguna fila ni movimiento. |  | pendiente |  |  |
| INV-010 | Catálogo público de repuestos | Catálogo habilitado; artículos públicos/privados de varios tipos. | 1. Sin iniciar sesión, abrir `/repuestos/`. 2. Buscar por nombre/código y combinar categoría, tipo y orden. 3. Limpiar filtros. 4. Abrir y cerrar la ficha de un artículo con teclado y móvil. | Solo aparecen artículos activos y públicos; filtros y limpieza funcionan; ficha y controles son utilizables en teclado y móvil. |  | pendiente |  |  |
| INV-011 | Datos internos no publicados | Hay costos, cantidades, mínimos, proveedor y ubicación distintos en dos sedes. | 1. Abrir catálogo y ficha pública. 2. Revisar texto visible y código fuente de la respuesta con ayuda del evaluador técnico. 3. Comparar un artículo sin stock público. | No aparecen costos, cantidades exactas, reservas, mínimos, proveedor, ubicación ni movimientos; solo disponibilidad cualitativa y sedes públicas. |  | pendiente |  |  |
| INV-012 | Catálogo deshabilitado | Responsable QA puede cambiar el flag del catálogo y reiniciar solo el entorno de prueba. | 1. Deshabilitar el catálogo. 2. Recargar navegación pública. 3. Abrir `/repuestos/` directamente. 4. Restaurar el valor inicial. | El enlace desaparece y la URL directa responde de forma controlada; inventario interno sigue funcionando. |  | pendiente |  |  |

## Checklist

- [ ] `INV-001` ejecutado.
- [ ] `INV-002` ejecutado.
- [ ] `INV-003` ejecutado.
- [ ] `INV-004` ejecutado.
- [ ] `INV-005` ejecutado.
- [ ] `INV-006` ejecutado.
- [ ] `INV-007` ejecutado.
- [ ] `INV-008` ejecutado.
- [ ] `INV-009` ejecutado.
- [ ] `INV-010` ejecutado.
- [ ] `INV-011` ejecutado.
- [ ] `INV-012` ejecutado.
- [ ] Validaciones de servidor comprobadas, no sólo controles visuales.
- [ ] Aislamiento de datos propios y de otra persona o sucursal comprobado también por URL directa.
- [ ] Responsive revisado en la pantalla principal.

## Integraciones, bloqueos y conformidad

No ajustar stock real; documentar cantidad antes/después de cada caso.

- Incidencias:
- Bloqueos externos:
- Observaciones:
- Conformidad: `conforme` / `con reservas` / `no conforme`.
