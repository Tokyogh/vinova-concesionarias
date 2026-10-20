# Roles y permisos

Fuente ejecutable: `apps/accounts/management/commands/seed_roles.py`. El corte
actual contiene 13 roles y 63 `PermissionCode`.

Vinova Pro combina usuario, uno o más roles, sucursal, vigencia temporal, ownership, estado y permisos por código. Un permiso visible en la interfaz no sustituye la autorización del backend.

## Administración

- Login: `/accounts/login/`.
- Usuarios: `/accounts/users/`.
- Roles: `/accounts/roles/`.
- Los roles pueden ser globales o limitarse a una sucursal.
- Las asignaciones pueden tener inicio, fin y estado activo.
- Solo permisos globales autorizados administran configuración transversal, seguridad, continuidad, SRI y QA.

## Roles base

`seed_roles` mantiene estos 13 códigos de rol oficiales: `superadmin`, `admin_general` (administrador general), `admin_sucursal` (administrador de sucursal), `gerente_comercial`, `jefe_inventario`, `vendedor`, `asesor_postventa`, `facturacion`, `bodega`, `marketing`, `soporte_cliente`, `auditor` y `cliente`. `superadmin` es un rol sembrado distinto del indicador Django `is_superuser`; no se deben tratar como equivalentes sin revisar el control de autorización de cada operación.

No asigne privilegios por nombre del rol desde código nuevo. Use los códigos de permiso definidos en `apps/accounts/management/commands/seed_roles.py` y aplique alcance de sucursal en selectores, vistas, API, tareas, reportes y exportaciones.

## Operación

```bash
docker compose run --rm web python manage.py seed_roles
```

El comando es idempotente. Revise periódicamente asignaciones vencidas, cuentas inactivas y roles globales. Los cambios críticos quedan registrados en auditoría.

## Alcance efectivo

Un permiso solo es efectivo si cuenta, rol y asignación están activos y la
ventana `starts_at`/`expires_at` está vigente. Una asignación con sucursal solo
cubre esa sede; `branch=NULL` es global. Recursos cliente agregan ownership por
expediente. Cuentas inactivas no conservan bypass de dominio, incluso si tienen
el flag Django de superusuario.

## Acceso Staff basado en riesgo

RBAC sigue siendo obligatorio aunque la política adaptativa permita una sesión.
En modo `enforce`, una cuenta Staff fuera de las CIDR confiables no entra a
paneles ni APIs privilegiadas hasta obtener una aprobación temporal para su
sesión, IP y señal de navegador. La decisión requiere una cuenta distinta, de
rango superior, con 2FA verificado y permiso global
`security.approve_staff_access`; se impiden autoaprobaciones y rangos iguales.

La política se entrega en `off`. Antes de activar `enforce` deben probarse red o
VPN, aprobadores, expiración/revocación y el comando de recuperación documentado
en [acceso Staff adaptativo](seguridad-avanzada/08-acceso-staff-adaptativo.md).

La matriz exhaustiva rol × permiso × operación × módulo × recurso × sucursal,
incluidas pruebas y ambigüedades conservadas, está en
[`auditoria-integral/04-matriz-rbac.md`](auditoria-integral/04-matriz-rbac.md).
