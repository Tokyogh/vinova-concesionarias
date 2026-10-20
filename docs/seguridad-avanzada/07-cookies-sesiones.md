# F7 — Cookies, almacenamiento del navegador y sesiones

Fecha: 2026-10-16

## Inventario comprobado

| Tecnología | Contenido | Clasificación | Protección |
|---|---|---|---|
| cookie de sesión | identificador opaco de sesión Django | estrictamente necesaria | `HttpOnly`, `SameSite=Lax`; `Secure` y prefijo `__Host-` en producción |
| cookie CSRF | valor antifalsificación Django | estrictamente necesaria | `SameSite=Lax`; `Secure` y prefijo `__Host-` en producción; legible por el navegador según el patrón CSRF de Django |
| `localStorage` de tema | preferencia claro/oscuro | preferencia local | sin identidad, token ni dato empresarial |
| `localStorage` de favoritos públicos | identificadores visuales de vehículos | preferencia local | sin credenciales; no autoriza operaciones |
| `localStorage` de navegación y filtros | recientes, favoritos internos y URLs de vistas guardadas por usuario | funcional y potencialmente identificable | claves separadas por usuario y limpieza al enviar logout |
| almacenamiento HTMX | prueba técnica y caché histórica del proveedor | no necesario para VINOVA | caché histórica desactivada (`historyCacheSize=0`) |

No se encontraron contraseñas, tokens de sesión, secretos 2FA ni claves API almacenados deliberadamente en JavaScript. El consentimiento y clasificación jurídica de preferencias se completa en F9.

## Controles aplicados

- Producción usa `__Host-vinova_session` y `__Host-vinova_csrf`, con `Secure`, ruta `/` y sin dominio compartido.
- La sesión productiva expira al cerrar el navegador por defecto y aplica tanto timeout por inactividad como duración absoluta configurable (ocho horas inicialmente), aunque exista actividad continua.
- El login rota una sesión anónima; logout invalida la sesión y marca su registro rastreado.
- El cambio de contraseña rota la sesión actual, revoca las demás y crea un registro nuevo para la sesión conservada.
- El restablecimiento por correo usa el servicio de historial/auditoría y revoca todas las sesiones existentes.
- HTMX no evalúa expresiones, no ejecuta etiquetas de script recibidas y no conserva HTML histórico en storage; el estilo interno recibe el nonce CSP.
- Al enviar logout se eliminan vistas guardadas y navegación interna del almacenamiento local del navegador. Tema y favoritos públicos se conservan como preferencias no autenticantes.
- Los checks de despliegue rechazan una ruptura del contrato `__Host-`.

## Evidencia

- `apps/security_center/tests/test_cookie_session_hardening.py`: rotación de login, cambio y reset de contraseña, timeout inactivo y configuración HTMX.
- `apps/security_center/tests/test_deployment_checks_v170.py`: prefijos y alcance de cookies productivas.
- `tests/security/production_settings_probe.py`: carga aislada de settings de producción.
- Regresión focal: 90 pruebas aprobadas.
- Regresión amplia de cuentas y seguridad: 1.883 pruebas aprobadas y 1 omisión declarada.
- Django check, drift de migraciones, Ruff y sintaxis JavaScript: aprobados.

## Riesgos residuales y decisiones

- La limpieza de `localStorage` en logout es una defensa del navegador y no sustituye el borrado manual de datos del sitio en equipos compartidos si JavaScript está deshabilitado.
- `SameSite=Lax` conserva flujos normales de navegación; CSRF sigue validándose con middleware y token, no se delega a SameSite.
- La validez de DNS, TLS, proxy y expiración real debe comprobarse de nuevo en staging candidato.
- Las preferencias no esenciales y cualquier proveedor opcional se gobiernan en F9; no se anticipa una base jurídica sin revisión.
