# Testeo beta — módulo Privacidad y auditoría

## Objetivo

Validar elección de cookies, consentimientos, solicitudes, exportación/anonimización y trazabilidad íntegra.

## Roles y permisos

`privacy.view/manage/export/anonymize`, `audit.view/export/manage_alerts` según rol y sede.

## Requisitos previos

- Navegador con datos del sitio borrados, clientes sintéticos, dos sedes y usuario autorizado separado para acciones críticas.
- Entorno y commit registrados en la plantilla individual.
- Datos sintéticos identificables y evidencia sin secretos.

## Casos

| ID | Módulo | Precondiciones | Pasos numerados | Resultado esperado observable | Resultado obtenido | Estado | Evidencia | Observaciones |
|---|---|---|---|---|---|---|---|---|
| PA-001 | Consentimiento | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Crear/retirar consentimiento con propósito y evidencia sintéticos. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Estado, versión, fecha y fuente quedan trazables. |  | pendiente |  |  |
| PA-002 | Solicitud pública | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Enviar solicitud con datos mínimos y abrir confirmación. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Se crea caso pendiente sin entregar datos automáticamente. |  | pendiente |  |  |
| PA-003 | Verificar identidad | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Registrar verificación por flujo autorizado. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Sólo rol permitido avanza y queda actor/fecha. |  | pendiente |  |  |
| PA-004 | Estados de solicitud | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Recorrer transiciones válidas y forzar una inválida. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Secuencia válida persiste; salto inválido se rechaza. |  | pendiente |  |  |
| PA-005 | Exportar datos | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Generar export para caso verificado con permiso. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Archivo contiene sólo sujeto/alcance y queda protegido/auditado. |  | pendiente |  |  |
| PA-006 | Anonimizar | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Ejecutar sobre cliente desechable con permiso y precondiciones. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Campos definidos se anonimizan sin romper integridad referencial; no se revierte silenciosamente. |  | pendiente |  |  |
| PA-007 | Retención | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Crear/editar política y evaluar registros elegibles. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Criterios/estado son visibles; no borra fuera del servicio autorizado. |  | pendiente |  |  |
| PA-008 | Scope privacidad | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Abrir caso/consentimiento de otra sede. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Se deniega y no se exporta información ajena. |  | pendiente |  |  |
| PA-009 | Evento de auditoría | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Realizar una mutación normal y buscar su evento. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Acción, actor, objeto, sede, request ID y snapshots esperados coinciden. |  | pendiente |  |  |
| PA-010 | Filtros y export de auditoría | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Filtrar por actor/acción/fecha/sede y exportar. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Pantalla/export coinciden y respetan `audit.export`. |  | pendiente |  |  |
| PA-011 | Integridad encadenada | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Ejecutar verificador antes y después de alterar sólo fixture de laboratorio. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Cadena limpia aprueba; manipulación se detecta sin reescribir historial. |  | pendiente |  |  |
| PA-012 | Fallo del registro externo | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Simular fallo del registro durante una denegación/error controlado. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Respuesta original se conserva y el fallo queda observable en logs. |  | pendiente |  |  |
| PA-013 | Redacción | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Provocar evento con campos sensibles sintéticos. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Tokens, contraseñas, cookies y secretos aparecen redactados, no en claro. |  | pendiente |  |  |
| PA-014 | Aceptar, rechazar o configurar cookies | Navegador limpio y página pública abierta. | 1. Comprobar que ninguna opción opcional esté marcada. 2. Rechazar todo y recargar. 3. Borrar datos del sitio, aceptar todo y recargar. 4. Repetir eligiendo solo una categoría. | Las tres acciones son visibles y equivalentes; la elección persiste sin pedir nombre, correo ni cuenta. |  | pendiente |  |  |
| PA-015 | Bloqueo antes de aceptar | Navegador limpio; analítica y mapa configurados en QA. | 1. Abrir un vehículo y la página de Instituciones sin decidir. 2. Revisar que no aparezca el mapa ni se registre la vista analítica. 3. Aceptar cada categoría por separado y repetir. | Antes de aceptar no carga el proveedor ni se crea analítica; cada función se habilita solo con su categoría. |  | pendiente |  |  |
| PA-016 | Cambiar y retirar la elección | Existe una elección previa con las tres categorías permitidas. | 1. Abrir “Preferencias de cookies” desde una página pública y desde el portal. 2. Retirar todas las categorías opcionales. 3. Recargar mapa y vehículo. 4. Cerrar sesión y comprobar que no quedan vistas internas guardadas. | La retirada apaga mapa/analítica y limpia preferencias locales conocidas; sesión y protección de formularios siguen funcionando. |  | pendiente |  |  |
| PA-017 | Textos legales pendientes de revisión | Sitio público con documentos legales configurados para beta. | 1. Abrir privacidad, cookies, términos y aviso legal desde el pie. 2. Revisar versión/fecha y enlaces de preferencias. 3. Buscar datos empresariales marcados como pendientes. 4. No aprobar contenido jurídico durante esta prueba. | Los textos son accesibles y versionados; campos desconocidos se muestran como pendientes y no como datos inventados ni aprobación legal. |  | pendiente |  |  |

## Checklist

- [ ] `PA-001` ejecutado.
- [ ] `PA-002` ejecutado.
- [ ] `PA-003` ejecutado.
- [ ] `PA-004` ejecutado.
- [ ] `PA-005` ejecutado.
- [ ] `PA-006` ejecutado.
- [ ] `PA-007` ejecutado.
- [ ] `PA-008` ejecutado.
- [ ] `PA-009` ejecutado.
- [ ] `PA-010` ejecutado.
- [ ] `PA-011` ejecutado.
- [ ] `PA-012` ejecutado.
- [ ] `PA-013` ejecutado.
- [ ] `PA-014` ejecutado.
- [ ] `PA-015` ejecutado.
- [ ] `PA-016` ejecutado.
- [ ] `PA-017` ejecutado.
- [ ] Validaciones de servidor comprobadas, no sólo controles visuales.
- [ ] Aislamiento de datos propios y de otra persona o sucursal comprobado también por URL directa.
- [ ] Responsive revisado en la pantalla principal.

## Integraciones, bloqueos y conformidad

Anonimización sólo sobre datos desechables; revisión legal sigue siendo gate externo.

- Incidencias:
- Bloqueos externos:
- Observaciones:
- Conformidad: `conforme` / `con reservas` / `no conforme`.
