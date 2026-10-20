# Testeo beta — módulo Reportes, analítica e importaciones

## Objetivo

Validar filtros, exportaciones, BI, agregados y lotes CSV/XLSX.

## Roles y permisos

`reports.view`, `data.export`, `analytics.view/export`, `leads.export`, `imports.manage` según rol/sede.

## Requisitos previos

- Datos sintéticos en dos sucursales y archivos CSV/XLSX controlados.
- Entorno y commit registrados en la plantilla individual.
- Datos sintéticos identificables y evidencia sin secretos.

## Casos

| ID | Módulo | Precondiciones | Pasos numerados | Resultado esperado observable | Resultado obtenido | Estado | Evidencia | Observaciones |
|---|---|---|---|---|---|---|---|---|
| RAI-001 | Reporte filtrado | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Aplicar fechas, sede, estado y tipo en un reporte operativo. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Tabla, métricas y querystring coinciden con filtros. |  | pendiente |  |  |
| RAI-002 | Exportar reporte | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Exportar el mismo filtro y comparar filas/totales. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Archivo corresponde a pantalla y no contiene columnas no autorizadas. |  | pendiente |  |  |
| RAI-003 | Scope de reporte | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Con rol de sede, incluir datos distinguibles de otra sede. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Pantalla y export omiten completamente la sede ajena. |  | pendiente |  |  |
| RAI-004 | Dashboard analítico | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Abrir periodo comercial y contrastar leads/ventas/interacciones. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Agregados coinciden con registros fuente y rango temporal. |  | pendiente |  |  |
| RAI-005 | Export analítico | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Exportar con y sin permiso específico. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Autorizado obtiene dataset scoped; no autorizado recibe denegación. |  | pendiente |  |  |
| RAI-006 | BI/API dataset | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Consultar dataset con permiso y token autorizado y límites. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Paginación, periodo y sede se respetan; el token no amplía los permisos del usuario. |  | pendiente |  |  |
| RAI-007 | Plantilla de importación | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Descargar plantilla por tipo y revisar datos/ejemplo/instrucciones. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Encabezados aceptados y hoja ejemplo están separados de datos. |  | pendiente |  |  |
| RAI-008 | Parsear CSV/XLSX | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Cargar versiones válidas equivalentes. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Ambos formatos generan filas normalizadas coherentes. |  | pendiente |  |  |
| RAI-009 | Prevalidación | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Cargar duplicados, referencias ausentes y formatos inválidos. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Cada fila muestra error preciso sin aplicar cambios de dominio. |  | pendiente |  |  |
| RAI-010 | Revalidación | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Corregir archivo/lote permitido y ejecutar validar otra vez. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Errores/contadores se reemplazan de forma determinista. |  | pendiente |  |  |
| RAI-011 | Confirmación | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Confirmar lote válido una vez y reintentar. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Cambios se aplican atómicamente; reintento no duplica. |  | pendiente |  |  |
| RAI-012 | Permiso y sucursal | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Abrir/confirmar lote ajeno o sin `imports.manage`. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Acceso y mutación se deniegan sin revelar filas. |  | pendiente |  |  |
| RAI-013 | Módulo/tipo excluido | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Intentar usar import histórico LITE o tipo no soportado. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | No se ofrece ni acepta; se documenta como exclusión, no como fallo. |  | pendiente |  |  |
| RAI-014 | Límites del archivo | Responsable QA prepara archivos que superan por una fila o columna los límites del entorno. | 1. Cargar CSV y XLSX justo dentro del límite. 2. Cargar versiones con demasiadas filas/columnas. 3. Cargar XLSX con enlace externo. 4. Revisar el lote rechazado. | Los archivos permitidos se prevalidan; los excesivos o inseguros se rechazan con mensaje claro, sin cambios ni archivo privado residual. |  | pendiente |  |  |

## Checklist

- [ ] `RAI-001` ejecutado.
- [ ] `RAI-002` ejecutado.
- [ ] `RAI-003` ejecutado.
- [ ] `RAI-004` ejecutado.
- [ ] `RAI-005` ejecutado.
- [ ] `RAI-006` ejecutado.
- [ ] `RAI-007` ejecutado.
- [ ] `RAI-008` ejecutado.
- [ ] `RAI-009` ejecutado.
- [ ] `RAI-010` ejecutado.
- [ ] `RAI-011` ejecutado.
- [ ] `RAI-012` ejecutado.
- [ ] `RAI-013` ejecutado.
- [ ] `RAI-014` ejecutado.
- [ ] Validaciones de servidor comprobadas, no sólo controles visuales.
- [ ] Aislamiento de datos propios y de otra persona o sucursal comprobado también por URL directa.
- [ ] Responsive revisado en la pantalla principal.

## Integraciones, bloqueos y conformidad

La importación histórica LITE sigue excluida; no cargar datos reales.

- Incidencias:
- Bloqueos externos:
- Observaciones:
- Conformidad: `conforme` / `con reservas` / `no conforme`.
