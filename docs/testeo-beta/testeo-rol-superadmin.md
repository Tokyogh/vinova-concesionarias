# Testeo beta — rol Superadministración

## Objetivo

Validar manualmente el contrato del rol `superadmin` sin ampliar privilegios ni alcance.

## Rol, permisos y alcance

- Código: `superadmin`.
- Alcance esperado: Global; rol del sistema distinto del flag Django `is_superuser`.
- Permisos: Los 63 `PermissionCode` vigentes de la matriz canónica.
- Funciones a probar: administración completa de cuentas, empresa, sucursales, operación, seguridad, privacidad, auditoría, integraciones, continuidad y QA; incluir `AS-011..AS-015`, `PA-014..PA-017` e `IC-018`; SRI operativo sigue excluido.

La fuente de verdad es [la matriz de permisos](../auditoria-integral/04-matriz-rbac.md) (RBAC significa control de acceso según el rol); un permiso sólo es efectivo con cuenta, rol, asignación y módulo activos.

## Requisitos previos

- Entorno local/QA/staging autorizado y commit registrado.
- Cuenta exclusiva para el rol, sin flags Django adicionales.
- Asignación vigente con el alcance indicado.
- Datos sintéticos; dos sucursales o expedientes cuando el caso exige aislamiento.
- Copia de [la plantilla de ejecución](testeo-plantilla-ejecucion.md).

## Casos

| ID | Caso | Precondiciones | Pasos numerados | Resultado esperado observable | Resultado obtenido | Estado | Evidencia | Observaciones |
|---|---|---|---|---|---|---|---|---|
| RSA-001 | Acceso y navegación | Cuenta activa con asignación vigente. | 1. Iniciar sesión. 2. Abrir el dashboard. 3. Recorrer sólo las entradas visibles del menú. 4. Volver con navegación del producto. | El perfil de dashboard corresponde al rol; no aparecen acciones ajenas y no hay errores técnicos. |  | pendiente |  |  |
| RSA-002 | Funciones permitidas | Datos sintéticos y módulos requeridos habilitados. | 1. Abrir todas las guías modulares; omitir únicamente exclusiones expresas. 2. Ejecutar un caso de lectura por cada área indicada. 3. Confirmar filtros y datos persistidos. | Las funciones visibles coinciden con: administración completa de cuentas, empresa, sucursales, operación, seguridad, privacidad, auditoría, integraciones, continuidad y QA; SRI operativo sigue excluido. |  | pendiente |  |  |
| RSA-003 | Mutación principal | Entorno no productivo y registros creados para esta ejecución. | 1. Registrar estado inicial. 2. Crear o editar un registro sintético de bajo riesgo, verificar persistencia y evento de auditoría; para restore/anonimización use sólo simulación sin cambios o entorno desechable. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | La respuesta es controlada, la persistencia coincide con la acción y la auditoría existe cuando aplica. |  | pendiente |  |  |
| RSA-004 | Denegación por permiso o estado | URL objetivo conocida sin alterar el rol. | 1. Registrar estado inicial. 2. Desactivar la cuenta de prueba o el módulo objetivo desde otra sesión autorizada e intentar una URL directa. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | La cuenta inactiva o el módulo OFF queda denegado aunque el rol conserve permisos. |  | pendiente |  |  |
| RSA-005 | Alcance y acceso horizontal | Dos sucursales o dos expedientes con datos distinguibles. | 1. Registrar estado inicial. 2. Abrir recursos sintéticos de dos sucursales y confirmar alcance global sin mezclar filtros ni atribuciones. 3. Recargar y contrastar persistencia/denegación. 4. Guardar evidencia redactada. | La respuesta respeta el alcance descrito; no mezcla listados, exports, archivos ni mutaciones. |  | pendiente |  |  |
| RSA-006 | Sesión, ayuda y responsive | Navegador de escritorio y viewport móvil. | 1. Abrir ayuda contextual. 2. Repetir dashboard y una lista a 360 px y escritorio. 3. Cerrar sesión por la acción POST. 4. Usar Atrás y reabrir una URL privada. | Controles utilizables sin solapamiento; ayuda corresponde al rol; tras logout no reaparece contenido privado. |  | pendiente |  |  |

## Checklist

- [ ] `RSA-001` ejecutado y documentado.
- [ ] `RSA-002` ejecutado y documentado.
- [ ] `RSA-003` ejecutado y documentado.
- [ ] `RSA-004` ejecutado y documentado.
- [ ] `RSA-005` ejecutado y documentado.
- [ ] `RSA-006` ejecutado y documentado.
- [ ] No se modificaron permisos para obtener un resultado favorable.
- [ ] Evidencia redactada y sin secretos.

## Incidencias y conformidad

- Incidencias relacionadas:
- Observaciones del rol:
- Conformidad: `conforme` / `con reservas` / `no conforme`.
- Evaluador y fecha: completar en la ficha separada.
