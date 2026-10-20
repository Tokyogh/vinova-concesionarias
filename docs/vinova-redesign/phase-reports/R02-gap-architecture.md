# R02 — Arquitectura y brechas funcionales (informe de fase)

**Fase:** R02 · **Estado:** COMPLETADA · **Iniciativa:** VINOVA_PRO_FUNCTIONAL_REDESIGN

## 1. Referencia investigada

Filas PENDIENTE de `functional-parity-matrix.md` (27) contrastadas con los modelos Django existentes (83 clases en 26 apps).

## 2. Funcionalidades diseñadas

Diseño concreto para las 27 brechas en `data-model-map.md` (§A modelos, §B permisos, §C diseño por fila, §D alcance de fases):

- **Modelos nuevos**: `VehicleLinkCode`, `CustomerVehicle`, `MaintenanceRule`, `NotificationPreference`, `ModuleDefinition`, campo `User.avatar`.
- **Extensiones**: `ServiceOrder` (recepción/km/void), `Branch` (geo), `Customer` (data migration de identificación).
- **Nueva app**: `apps/portal` (R07, módulo opcional con `portal.access`).
- **Servicios/flux**: adaptador de storage (`STORAGE_BACKEND`), validadores ecuatorianos, deduplicación difusa, eventos de notificación, PDF WeasyPrint.

## 3. Diferencias justificadas

Tabla cuenta↔expediente↔vehículo separada (AGENTS §12); sin VIN degradado; sin fusión automática de expedientes; sin enlaces estáticos públicos para manuales; módulos OFF reales (404), no solo CSS.

## 4. Modelos/migraciones previstas

7 migraciones nuevas (accounts, customers, vehicles, post_sales×2, branches, notifications, common) + data migrations; ninguna ejecutada en R02 (fase de diseño).

## 5. Seguridad y permisos

5 códigos de permiso nuevos (`portal.access`, `vehicles.link_codes`, `post_sales.reception`, `maintenance.rules`, `branches.geo`); ownership por destinatario/dueño; transacciones con advisory lock en canjes.

## 6. Pruebas ejecutadas

- `python manage.py check` → **OK, sin errores**.
- Sin cambios funcionales: no corresponde suite.

## 7. Fallos pendientes

Los 5 preexistentes de R00 (no atribuibles).

## 8. Commit local

`R02: architecture and gap design - proposed models, permissions, migrations` (docs únicamente).

## 9. Próxima fase y punto de reanudación

- **Siguiente:** R03 — Clientes e identificación (validadores cédula/RUC, normalización, deduplicación, auditoría de identificación).
- **Reanudar en:** `data-model-map.md` §C filas F09/F10/F11/F15; implementar en `apps/common/validators.py`, `apps/common/normalization.py`, `apps/customers/services.py` + tests.
