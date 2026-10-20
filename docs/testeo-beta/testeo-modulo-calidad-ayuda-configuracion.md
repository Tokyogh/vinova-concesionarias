# Testeo beta — módulo Calidad, ayuda y configuración modular

## Objetivo

Validar interruptor del módulos, runner QA, ayuda, errores, responsive y gates de release.

## Roles y permisos

`enterprise.manage`/configuración, `quality.view/run`, `help.view/manage`; superficies públicas y todos los roles.

## Requisitos previos

- Entorno QA, dos módulos con flags controlables, navegador Chromium y viewport móvil/escritorio.
- Entorno y commit registrados en la plantilla individual.
- Datos sintéticos identificables y evidencia sin secretos.

## Casos

| ID | Módulo | Precondiciones | Pasos numerados | Resultado esperado observable | Resultado obtenido | Estado | Evidencia | Observaciones |
|---|---|---|---|---|---|---|---|---|
| QAC-001 | Módulo ON | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Habilitar módulo opcional y abrir menú/ruta con rol permitido. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Navegación y backend exponen sólo funciones autorizadas. |  | pendiente |  |  |
| QAC-002 | Módulo OFF | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Deshabilitarlo manteniendo permisos y abrir URL directa. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Menú desaparece y backend bloquea sin debilitar otros módulos. |  | pendiente |  |  |
| QAC-003 | Persistencia de configuración | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Guardar configuración válida/inválida y reiniciar sólo proceso QA si procede. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Válida persiste; inválida se rechaza y no deja estado parcial. |  | pendiente |  |  |
| QAC-004 | Perfil QA | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Ejecutar perfil quick/full permitido y revisar pasos. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Reporte lista comando, estado, duración y evidencia sin secretos. |  | pendiente |  |  |
| QAC-005 | Protección QA | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Intentar ejecutar/descargar resultado sin permisos o de otro alcance. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Se deniega; no se expone salida privada. |  | pendiente |  |  |
| QAC-006 | Ayuda por rol | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Buscar artículo/checklist desde dos roles distintos. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Contenido/context tip corresponde al rol y módulo, sin enlaces rotos. |  | pendiente |  |  |
| QAC-007 | Gestión de ayuda | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Crear/editar contenido sintético y alternar publicación. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Sólo autorizado modifica; público/roles ven únicamente lo publicado. |  | pendiente |  |  |
| QAC-008 | Responsive y accesibilidad | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Recorrer portada, lista, formulario, tabla y modal a 360/768/1440 px con teclado. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Sin solapamiento; foco, labels, contraste/semántica y cierre de modal son utilizables. |  | pendiente |  |  |
| QAC-009 | Errores seguros | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Provocar 403, 404 y error controlado en QA. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Página comprensible sin traceback, secretos ni detalles internos. |  | pendiente |  |  |
| QAC-010 | Release y skips | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Ejecutar checks de release y clasificar skips/gates. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Resultado distingue aprobado, omitido y bloqueado; no declara readiness por automatización sola. |  | pendiente |  |  |
| QAC-011 | Documentación interna bilingüe | Commit candidato disponible para el responsable técnico. | 1. Ejecutar la auditoría documental estricta. 2. Abrir una muestra Python, template, CSS, JavaScript y script operativo. 3. Confirmar español primero e inglés después. 4. Registrar cualquier comentario incorrecto como incidencia. | La herramienta informa cero faltantes y la muestra explica responsabilidad y bloques relevantes sin cambiar la función. |  | pendiente |  |  |

## Checklist

- [ ] `QAC-001` ejecutado.
- [ ] `QAC-002` ejecutado.
- [ ] `QAC-003` ejecutado.
- [ ] `QAC-004` ejecutado.
- [ ] `QAC-005` ejecutado.
- [ ] `QAC-006` ejecutado.
- [ ] `QAC-007` ejecutado.
- [ ] `QAC-008` ejecutado.
- [ ] `QAC-009` ejecutado.
- [ ] `QAC-010` ejecutado.
- [ ] `QAC-011` ejecutado.
- [ ] Validaciones de servidor comprobadas, no sólo controles visuales.
- [ ] Aislamiento de datos propios y de otra persona o sucursal comprobado también por URL directa.
- [ ] Responsive revisado en la pantalla principal.

## Integraciones, bloqueos y conformidad

Aprobación visual humana, staging y proveedores se reportan por separado.

- Incidencias:
- Bloqueos externos:
- Observaciones:
- Conformidad: `conforme` / `con reservas` / `no conforme`.
