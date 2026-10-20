# Testeo beta — módulo API, integraciones y continuidad

## Objetivo

Validar clientes API, permisos API, idempotencia, webhooks, BI, backups y transferencias.

## Roles y permisos

`integrations.view/manage`, permisos de dataset, `continuity.view/manage/restore`.

## Requisitos previos

- Entorno aislado, endpoint local controlado, storage QA y claves sintéticas.
- Entorno y commit registrados en la plantilla individual.
- Datos sintéticos identificables y evidencia sin secretos.

## Casos

| ID | Módulo | Precondiciones | Pasos numerados | Resultado esperado observable | Resultado obtenido | Estado | Evidencia | Observaciones |
|---|---|---|---|---|---|---|---|---|
| IC-001 | Cliente API y secreto | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Crear cliente y capturar el secreto mostrado una sola vez. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Hash persiste; el secreto no vuelve a mostrarse ni aparece en logs. |  | pendiente |  |  |
| IC-002 | Scopes | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Solicitar endpoint dentro/fuera de permisos API. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | El permiso de integración funciona junto con los permisos del usuario; si falta uno, se deniega. |  | pendiente |  |  |
| IC-003 | Sesión y bearer | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Comparar autenticación interna y token API en rutas correspondientes. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Cada mecanismo sólo funciona en su superficie y cuenta activa. |  | pendiente |  |  |
| IC-004 | Idempotencia | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Repetir mutación con la misma clave y luego contenido enviado distinto. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Repetición devuelve resultado previo; conflicto se rechaza sin duplicar. |  | pendiente |  |  |
| IC-005 | Logs de integración | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Ejecutar solicitud válida/inválida y revisar log. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Metadatos útiles quedan sin credenciales/cuerpo sensible. |  | pendiente |  |  |
| IC-006 | URL de webhook | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Guardar HTTPS/local autorizado y probar loopback, privada o esquema peligroso. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Validador bloquea destinos SSRF y formatos prohibidos. |  | pendiente |  |  |
| IC-007 | Firma HMAC | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Entregar a receptor QA y verificar cabecera/firma. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Payload recibido valida con secreto correspondiente sin exponerlo. |  | pendiente |  |  |
| IC-008 | Retry y timeout | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Provocar timeout/5xx y luego recuperación. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Backoff/contador/estado siguen política; no duplica evento lógico. |  | pendiente |  |  |
| IC-009 | Endpoint inactivo | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Desactivar endpoint con entregas pendientes. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | No se envían nuevas entregas y el estado es auditable. |  | pendiente |  |  |
| IC-010 | OpenAPI y BI | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Abrir esquema/documentación y dataset autorizado. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Contrato corresponde a rutas; BI aplica ventana, límites, permisos API y sede. |  | pendiente |  |  |
| IC-011 | Crear backup | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Crear backup QA con manifest/cifrado/configuración disponible. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Registro, archivo, hash y metadatos quedan consistentes. |  | pendiente |  |  |
| IC-012 | Verificar backup | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Ejecutar verificación sobre backup válido y copia alterada. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Válido aprueba; alterado falla por integridad. |  | pendiente |  |  |
| IC-013 | Preparar restore/drill | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Preparar restauración y ejecutar sólo drill aislado. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | No toca entorno empresarial; evidencia y pasos quedan registrados. |  | pendiente |  |  |
| IC-014 | Exportar/validar transferencia | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Crear paquete `.vinova`, validar versión/firma/rutas y probar manipulación. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Paquete válido se acepta para preparación; manipulado/incompatible se bloquea. |  | pendiente |  |  |
| IC-015 | Gates externos | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Revisar almacenamiento, TLS, DNS, proveedor y restore real sin simular. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Cada dependencia queda `aprobada` con evidencia o `bloqueada`; nunca se infiere. |  | pendiente |  |  |
| IC-016 | Cambio de destino DNS | Laboratorio con hostname controlado que el responsable técnico pueda hacer resolver a una IP segura y luego a una privada. | 1. Validar el endpoint cuando resuelve al receptor QA. 2. Cambiar la resolución antes del envío. 3. Ejecutar una entrega de prueba. 4. Revisar estado y log redactado. | VINOVA no conecta a la IP nueva no permitida, no sigue redirecciones y registra un fallo controlado sin mostrar secretos. |  | pendiente |  |  |
| IC-017 | Límites y espacio de restore | Backup/transfer sintético y destino aislado con límites QA reducidos. | 1. Verificar paquete válido. 2. Probar copia con demasiados miembros o expansión. 3. Preparar restore hacia destino sin espacio suficiente. 4. Confirmar que el destino activo no cambió. | Los tres rechazos ocurren antes de extraer o reemplazar datos; archivo/ruta activa permanece intacta. |  | pendiente |  |  |
| IC-018 | Antivirus o cuarentena | Revisar con Operaciones si existe un motor desplegado para el candidato. | 1. Registrar proveedor, versión y flujo de cuarentena sin subir malware real. 2. Probar un archivo benigno autorizado. 3. Si no existe el control, marcar el caso `bloqueado`. 4. Adjuntar solo evidencia no sensible. | Solo se aprueba con cuarentena, resultado seguro y bloqueo previo de descarga demostrados; ausencia de motor nunca se marca aprobada. |  | pendiente |  |  |

## Checklist

- [ ] `IC-001` ejecutado.
- [ ] `IC-002` ejecutado.
- [ ] `IC-003` ejecutado.
- [ ] `IC-004` ejecutado.
- [ ] `IC-005` ejecutado.
- [ ] `IC-006` ejecutado.
- [ ] `IC-007` ejecutado.
- [ ] `IC-008` ejecutado.
- [ ] `IC-009` ejecutado.
- [ ] `IC-010` ejecutado.
- [ ] `IC-011` ejecutado.
- [ ] `IC-012` ejecutado.
- [ ] `IC-013` ejecutado.
- [ ] `IC-014` ejecutado.
- [ ] `IC-015` ejecutado.
- [ ] `IC-016` ejecutado.
- [ ] `IC-017` ejecutado.
- [ ] `IC-018` ejecutado.
- [ ] Validaciones de servidor comprobadas, no sólo controles visuales.
- [ ] Aislamiento de datos propios y de otra persona o sucursal comprobado también por URL directa.
- [ ] Responsive revisado en la pantalla principal.

## Integraciones, bloqueos y conformidad

Proveedores reales, DNS/TLS público y restauración empresarial requieren ventana/aprobación externa.

- Incidencias:
- Bloqueos externos:
- Observaciones:
- Conformidad: `conforme` / `con reservas` / `no conforme`.
