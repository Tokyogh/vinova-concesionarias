# F8 — Acceso Staff adaptativo

Fecha: 2026-10-16

## Estado seguro por defecto

La política se entrega en modo `off`; ninguna cuenta existente queda bloqueada al migrar. Los modos disponibles son:

- `off`: no evalúa restricciones adaptativas;
- `monitor`: audita una señal de riesgo por contexto sin bloquear;
- `enforce`: bloquea funciones internas y APIs privilegiadas hasta cumplir una red confiable o una aprobación temporal.

El modo estricto no puede guardarse sin al menos una IP/CIDR corporativa o VPN y otro aprobador global activo con 2FA. Las redes `/0` y configuraciones inválidas se rechazan.

## Evaluación y mínimo dato

En cada petición protegida se revalidan:

- IP actual frente a CIDR configuradas;
- sesión concreta;
- cambio de señal de navegador dentro de la sesión;
- vigencia, estado y contexto exacto de una aprobación.

La solicitud persiste hashes con clave del proyecto para IP, sesión y agente; no añade GPS, geolocalización por IP ni identificadores invasivos. El middleware de auditoría existente conserva su propio tratamiento de IP conforme a la política general.

## Flujo fuera de política

1. La cuenta mantiene autenticación básica, pero no recibe acceso a paneles ni API Staff.
2. Debe configurar y verificar 2FA en la sesión.
3. Se crea una solicitud idempotente, ligada a sesión, IP y señal del navegador, con expiración corta.
4. Se genera un aviso interno mínimo a los aprobadores; no incluye IP ni hashes.
5. Solo una cuenta distinta, de rango superior, con permiso global `security.approve_staff_access` y 2FA verificado puede aprobar o rechazar.
6. La aprobación concede acceso temporal al contexto solicitado; no asigna roles ni permisos.
7. La expiración, revocación, cambio de IP, cambio de navegador o cambio de sesión vuelve a bloquear.

Las decisiones usan bloqueo transaccional; una solicitud resuelta no puede reutilizarse. Se limitan nuevas solicitudes repetidas y todos los eventos relevantes quedan auditados.

## Alcance y recuperación

- Clientes y cuentas sin acceso interno no están sujetos a la política.
- Páginas públicas, perfil propio, 2FA, cambio de contraseña y estado/cancelación de la solicitud siguen disponibles.
- Las pantallas de aprobación permanecen dentro del perímetro adaptativo; un aprobador fuera de política también necesita su propio acceso válido.
- La recuperación operacional exige consola privilegiada y confirmación literal:

  `python manage.py disable_staff_access_policy --confirm DISABLE-STAFF-ACCESS`

El comando solo cambia el modo a `off` y genera auditoría de sistema. No crea usuarios, no concede roles y no modifica contraseñas.

## Evidencia

- `apps/security_center/tests/test_staff_adaptive_access.py`: 15 pruebas de red habitual, denegación, 2FA, idempotencia, aviso, rango, alcance global, API, aprobación, ventanas acotadas, replay, expiración, revocación, monitoreo, clientes y recuperación.
- Regresión integrada final de seguridad y cuentas: 938 pruebas aprobadas; regresión focal posterior: 25 aprobadas.
- Django check, drift de migraciones, Ruff global y compileall: aprobados.
- Migración `security_center.0004` aplicada en PostgreSQL local; permiso presente una vez y política en `off`.

## Riesgos residuales

- Las CIDR confiables requieren inventario empresarial correcto de oficina/VPN; no se activan automáticamente.
- Una cuenta de máxima autoridad fuera de red no puede autoaprobarse ni ser aprobada por rango igual; debe usar una ruta confiable o la recuperación de consola.
- La señal de navegador es auxiliar y no equivale a identidad fuerte del dispositivo.
- Proxy, VPN, DNS/TLS y operación real deben probarse en staging antes de habilitar `enforce`.
- IP y señales técnicas deben incluirse en la revisión de privacidad y retención F10.
