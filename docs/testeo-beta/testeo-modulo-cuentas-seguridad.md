# Testeo beta — módulo Cuentas y seguridad

## Objetivo

Validar autenticación, recuperación, 2FA, sesiones, usuarios, permisos vigentes y acceso Staff fuera de la red habitual.

## Roles y permisos

Administradores para gestión; cualquier cuenta para funciones propias. Permisos: `accounts.manage_users`, `accounts.assign_roles`, `security.view`, `security.manage`.

## Requisitos previos

- Cuenta administrativa autorizada, dos cuentas Staff sintéticas de distinto rango, correo QA y aplicación TOTP de prueba.
- Red o IP de QA marcada como confiable y otra fuera de política; la persona responsable debe poder devolver la política a `off`.
- Entorno y commit registrados en la plantilla individual.
- Datos sintéticos identificables y evidencia sin secretos.

## Casos

| ID | Módulo | Precondiciones | Pasos numerados | Resultado esperado observable | Resultado obtenido | Estado | Evidencia | Observaciones |
|---|---|---|---|---|---|---|---|---|
| AS-001 | Inicio y cierre de sesión | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Iniciar con usuario/correo válido, visitar una página privada, cerrar por el control POST y reabrirla. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Se crea sesión segura; después del logout la URL exige autenticación y Atrás no revela contenido privado. |  | pendiente |  |  |
| AS-002 | Credenciales inválidas y rate limit | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Enviar intentos inválidos controlados sin superar el límite acordado y luego usar credenciales válidas. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | El mensaje no enumera cuentas; bloqueo/rate limit es controlado y la cuenta válida recupera acceso conforme a política. |  | pendiente |  |  |
| AS-003 | Recuperación de contraseña | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Solicitar reset en Mailpit/QA, abrir una vez el enlace y establecer una contraseña conforme. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | No se revela si el correo existe; el token no se reutiliza y la sesión usa la nueva contraseña. |  | pendiente |  |  |
| AS-004 | 2FA y códigos de respaldo | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Activar TOTP, completar challenge, consumir un respaldo y probar un código inválido. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Sólo códigos vigentes permiten acceso; el respaldo consumido no funciona de nuevo. |  | pendiente |  |  |
| AS-005 | Sesiones activas | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Abrir dos sesiones, revisar dispositivos y revocar una desde la otra. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | La sesión revocada pierde acceso y la sesión actual conserva trazabilidad. |  | pendiente |  |  |
| AS-006 | Gestión de usuario | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Crear/editar una cuenta sintética, cambiar estado activo y revisar detalle. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | Campos validan unicidad/formato; al desactivar se pierde acceso y permisos de dominio. |  | pendiente |  |  |
| AS-007 | Asignación de rol | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Asignar rol con sucursal, inicio y expiración; revisar detalle. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | La asignación persiste exactamente y no permite un alcance prohibido para roles de sucursal. |  | pendiente |  |  |
| AS-008 | Rol futuro, expirado o revocado | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Probar la misma URL antes de inicio, después de expiración y con asignación desactivada. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | En los tres estados el permiso efectivo desaparece sin borrar historial. |  | pendiente |  |  |
| AS-009 | URL directa y CSRF | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Abrir una ruta no autorizada y enviar una mutación sin token CSRF. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | La ruta queda denegada y la mutación CSRF no cambia datos. |  | pendiente |  |  |
| AS-010 | Política e historial de contraseña | Requisitos previos del módulo y permiso aplicable. | 1. Registrar estado inicial. 2. Intentar una contraseña débil/reutilizada y luego una válida. 3. Recargar y contrastar persistencia/auditoría. 4. Guardar evidencia redactada. | La política e historial se aplican en servidor sin registrar la contraseña en logs o auditoría. |  | pendiente |  |  |
| AS-011 | Política Staff apagada y red habitual | Política inicialmente `off`; red QA autorizada disponible. | 1. Con la política apagada, iniciar sesión Staff y abrir el panel. 2. Activar primero `monitor` y repetir desde la red habitual. 3. Revisar el evento de seguridad con una cuenta autorizada. 4. No activar bloqueo todavía. | El modo apagado no bloquea; monitoreo permite entrar y registra la evaluación sin mostrar datos técnicos sensibles. |  | pendiente |  |  |
| AS-012 | Acceso Staff fuera de red | Política `enforce`, dos aprobadores válidos y cuenta solicitante con 2FA. | 1. Iniciar sesión desde el contexto QA fuera de red. 2. Intentar abrir el panel y una API interna. 3. Completar 2FA y enviar una sola solicitud. 4. Recargar la pantalla pendiente. | Panel y API siguen bloqueados; aparece una solicitud pendiente sin crear duplicados ni conceder permisos. |  | pendiente |  |  |
| AS-013 | Aprobar o rechazar acceso temporal | Existe la solicitud de `AS-012`; otra cuenta de rango superior tiene 2FA y permiso de aprobación. | 1. Abrir “Solicitudes de acceso Staff” con la segunda cuenta. 2. Rechazar una solicitud y confirmar que sigue bloqueada. 3. Crear otra solicitud y aprobarla por el tiempo QA acordado. 4. Volver a la sesión solicitante. | Una cuenta no se aprueba a sí misma; rechazo no habilita acceso y aprobación válida permite solo la sesión/contexto solicitado durante su vigencia. |  | pendiente |  |  |
| AS-014 | Expiración, cambio y revocación | Hay una aprobación temporal activa de `AS-013`. | 1. Abrir el panel autorizado. 2. Revocar la aprobación desde la cuenta superior y recargar. 3. Repetir en otra sesión o contexto de red QA. 4. Si el entorno lo permite, comprobar también la expiración corta. | Revocación, expiración o cambio de sesión/red vuelven a bloquear; la aprobación no se reutiliza ni asigna roles. |  | pendiente |  |  |
| AS-015 | Recuperación segura | Entorno desechable y responsable técnico presente; no usar producción. | 1. Confirmar que hay una cuenta de recuperación y registrar el estado. 2. Pedir al responsable ejecutar el comando documentado con su frase exacta. 3. Recargar la configuración. 4. Revisar el evento de auditoría. | La política vuelve a `off`; no se crean usuarios, no cambian contraseñas ni se conceden permisos. |  | pendiente |  |  |

## Checklist

- [ ] `AS-001` ejecutado.
- [ ] `AS-002` ejecutado.
- [ ] `AS-003` ejecutado.
- [ ] `AS-004` ejecutado.
- [ ] `AS-005` ejecutado.
- [ ] `AS-006` ejecutado.
- [ ] `AS-007` ejecutado.
- [ ] `AS-008` ejecutado.
- [ ] `AS-009` ejecutado.
- [ ] `AS-010` ejecutado.
- [ ] `AS-011` ejecutado.
- [ ] `AS-012` ejecutado.
- [ ] `AS-013` ejecutado.
- [ ] `AS-014` ejecutado.
- [ ] `AS-015` ejecutado.
- [ ] Validaciones de servidor comprobadas, no sólo controles visuales.
- [ ] Aislamiento de datos propios y de otra persona o sucursal comprobado también por URL directa.
- [ ] Responsive revisado en la pantalla principal.

## Integraciones, bloqueos y conformidad

No usar correos, teléfonos, contraseñas ni factores de personas reales.

- Incidencias:
- Bloqueos externos:
- Observaciones:
- Conformidad: `conforme` / `con reservas` / `no conforme`.
