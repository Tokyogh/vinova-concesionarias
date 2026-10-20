# Testeo beta — módulo Empresa, sucursales y portal público

## Objetivo

Validar configuración empresarial, sedes/instituciones y publicación geográfica.

## Roles y permisos

`superadmin` o `admin_general`; lectura pública sin login. Permisos: `companies.manage`, `branches.manage`, `enterprise.manage`, `approvals.manage`.

## Requisitos previos

- Empresa sintética configurada, dos sucursales, una imagen segura de prueba y clave pública de mapas sólo en entorno autorizado.
- Entorno y commit registrados en la plantilla individual.
- Datos sintéticos identificables y evidencia sin secretos.

## Casos

| ID | Módulo | Precondiciones | Pasos numerados | Resultado esperado observable | Resultado obtenido | Estado | Evidencia | Observaciones |
|---|---|---|---|---|---|---|---|---|
| ESP-001 | Perfil empresarial | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Editar nombre comercial, contacto y branding con valores sintéticos y recargar. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Los valores configurados aparecen donde corresponde sin reemplazar identidad de registros existentes. |  | pendiente |  |  |
| ESP-002 | Sitio público y legales | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Cambiar sólo campos públicos configurables y revisar portada/nosotros/contacto. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | La publicación usa configuración guardada y no expone campos internos. |  | pendiente |  |  |
| ESP-003 | Políticas de aprobación | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Crear/editar una política sintética y comprobar su activación. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | La política queda auditable y no autoriza operaciones fuera del servicio que la consume. |  | pendiente |  |  |
| ESP-004 | Crear sucursal | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Registrar código, nombre, contacto, horario, servicios, dirección y coordenadas válidas. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | La sede persiste una sola vez con todos los campos y evento de auditoría. |  | pendiente |  |  |
| ESP-005 | Editar ubicación | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Cambiar dirección/latitud/longitud y recargar gestión y mapa. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | El marcador y texto público reflejan la nueva ubicación sin caché obsoleta. |  | pendiente |  |  |
| ESP-006 | Publicación en directorio | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Activar una sede completa y abrir instituciones/portada sin login. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Sólo sedes activas/publicadas aparecen con contacto, horario y servicios disponibles. |  | pendiente |  |  |
| ESP-007 | Filtros y limpiar filtros | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Aplicar tipo/servicio/búsqueda, combinar opciones y usar la acción para limpiar. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Lista y marcadores coinciden; limpiar restaura todas las sedes sin parámetros residuales. |  | pendiente |  |  |
| ESP-008 | Desactivar sucursal | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Desactivar una sede sintética y volver al directorio/mapa. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Desaparece de superficies públicas sin eliminar historial ni recursos asociados. |  | pendiente |  |  |
| ESP-009 | Validaciones geográficas | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Enviar coordenadas fuera de rango, código duplicado y campos requeridos vacíos. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | El servidor rechaza cada entrada con mensaje comprensible y no crea cambios parciales. |  | pendiente |  |  |
| ESP-010 | Permisos y auditoría | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Intentar gestión con rol sin `branches.manage`; repetir con autorizado. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | El primer acceso se deniega; el segundo registra snapshots before/after correctos. |  | pendiente |  |  |
| ESP-011 | Foto y sitio web de la sede | Sede sintética y archivos JPG/PNG/WEBP seguros disponibles. | 1. Abrir la edición de la sede. 2. Cargar una imagen válida y escribir una URL HTTPS. 3. Guardar y abrir el directorio público. 4. Repetir con un archivo falso o URL no permitida. | La foto y el enlace válidos aparecen solo en la sede publicada; entradas inválidas muestran un mensaje y no cambian el registro. |  | pendiente |  |  |
| ESP-012 | Mapa y elección de privacidad | Navegador limpio, sede pública con coordenadas y MapTiler configurado en QA. | 1. Abrir Instituciones sin haber elegido cookies. 2. Rechazar contenido externo y usar búsqueda/filtros. 3. Abrir preferencias, permitir contenido externo y volver. 4. Retirar el permiso y recargar. | La lista y filtros siempre funcionan; el mapa y su proveedor solo cargan al permitir contenido externo y vuelven a apagarse al retirar el permiso. |  | pendiente |  |  |

## Checklist

- [ ] `ESP-001` ejecutado.
- [ ] `ESP-002` ejecutado.
- [ ] `ESP-003` ejecutado.
- [ ] `ESP-004` ejecutado.
- [ ] `ESP-005` ejecutado.
- [ ] `ESP-006` ejecutado.
- [ ] `ESP-007` ejecutado.
- [ ] `ESP-008` ejecutado.
- [ ] `ESP-009` ejecutado.
- [ ] `ESP-010` ejecutado.
- [ ] `ESP-011` ejecutado.
- [ ] `ESP-012` ejecutado.
- [ ] Validaciones de servidor comprobadas, no sólo controles visuales.
- [ ] Aislamiento de datos propios y de otra persona o sucursal comprobado también por URL directa.
- [ ] Responsive revisado en la pantalla principal.

## Integraciones, bloqueos y conformidad

Use únicamente imagen, URL y coordenadas sintéticas autorizadas; no invente datos de una empresa real.

- Incidencias:
- Bloqueos externos:
- Observaciones:
- Conformidad: `conforme` / `con reservas` / `no conforme`.
