# Data model map — web_carros/ ↔ VINOVA PRO (Django)

> R01. Equivalencias de entidades entre el proyecto original (SQLite crudo) y el modelo Django actual.
> Referencia: `docs/vinova-redesign/reference-inventory.md` §3.

## Tabla de equivalencias

| Entidad original (tabla) | Equivalente Django | Archivo | Notas de adaptación |
|---|---|---|---|
| `usuarios` | `accounts.User` (AbstractUser) | `apps/accounts/models.py` | Cédula no existe como campo único: pasar a `customers.Customer.identification_*` separado de la cuenta (AGENTS §12) |
| `usuarios.rol` (texto ADMIN/TRABAJADOR/USUARIO) | `Role` + `UserRole` + `PermissionCode` | `apps/accounts/models.py` | Sistema por código de permiso + alcance de sucursal: conservar |
| `usuarios.foto_perfil` (URL Cloudinary) | sin equivalente | — | R04: ImageField/URL + adaptador de storage |
| `usuarios.notificar_*` (5 flags) | sin equivalente | — | R11: modelo de preferencias de notificación |
| `usuarios.reset_token_hash/expira` | mecanismo de reset de Django | `apps/accounts/` | Verificar un solo uso y expiración (F02) |
| `clientes` (= usuarios rol USUARIO) | `customers.Customer` | `apps/customers/models.py` | Separar cuenta de autenticación de expediente (modelo ya separado) |
| `usuarios.cedula` (texto, sin UNIQUE) | `Customer.identification_number` + constraint parcial | `apps/customers/models.py:54-60` | Falta validador EC (F09) y dedupe difusa (F10) |
| `vehiculos` | `vehicles.Vehicle` (+ `VehicleBrand`, `VehicleModel`) | `apps/vehicles/models.py` | Original sin VIN; Django con `vin` único e `internal_code` |
| `vehiculos.imagen` (archivo único) | `VehicleMedia` / `VehicleResource` | `apps/vehicles/models.py:45-203` | Multimodal: conservar |
| `vehiculos.preview_sistemas_json`, `modelo_3d*` | sin equivalente | — | 3D es módulo opcional; evaluar en R02 |
| `vehiculo_modelos` | `VehicleModel` | `apps/vehicles/models.py` | El original deduplica identidad para manuales/3D |
| `usuarios_vehiculos` (garaje) | sin equivalente | — | R06: vínculo cliente↔vehículo con km inicial |
| `codigos_vehiculo` (códigos de canje) | sin equivalente | — | R06: modelo con códigos aleatorios, revocación, 1 por vehículo |
| `canjes_reversados` (snapshot) | sin equivalente | — | R06: tabla de reversa/auditoría |
| `mantenimientos` | `post_sales.ServiceOrder` (+Line, History) | `apps/post_sales/models.py` | Faltan: recepción, kilometraje, diagnóstico, reglas km/meses (R08) |
| `facturas_vehiculo` | `invoices.InvoiceRecord` (+Line, Sequence, StatusHistory) | `apps/invoices/models.py` | Django ya usa Decimal e impuestos por línea; falta generación de PDF (R10) |
| `factura_articulos` | `invoices.InvoiceLine` | `apps/invoices/models.py:123-159` | Vinculación a artículo → `inventory.InventoryItem` |
| `manuales_vehiculo` / `manuales_modelo` | `documents.PrivateDocument` / `ReusableAsset` (tipo manual) | `apps/documents/models.py` | Falta publicación por modelo y descarga al cliente (R09) |
| `articulos` | `inventory.InventoryItem` | `apps/inventory/models.py` | `codigo_articulo` ↔ `sku` único |
| `articulo_movimientos` | `inventory.StockMovement` | `apps/inventory/models.py` | Conserva stock_anterior/nuevo |
| `articulo_stock_establecimiento` | `inventory.BranchStock` | `apps/inventory/models.py` | UNIQUE(artículo, sucursal) equivalente |
| `establecimientos` | `branches.Branch` | `apps/branches/models.py` | Falta `lat`/`lng`, `servicios` JSON e `imagen` (R12/R13) |
| `notificaciones_usuario` | `notifications.NotificationMessage` + `NotificationRecipient` | `apps/notifications/models.py` | Falta "marcar todas" y preferencias (R11) |
| `auditoria_acciones` | `audit.AuditLog` (hash encadenado) | `apps/audit/models.py` | Django es más estricto: conservar |
| `mensajes_contacto` | flujo de contacto público / `leads` | `apps/leads/`, `apps/dashboard/` | Revisar en R13 |
| `schema_migrations` (runner manual) | migraciones Django | `apps/*/migrations/` | 45 archivos; conservar flujo hacia adelante |

## Entidades del original sin equivalente (brechas a construir)

1. Garaje del cliente (`usuarios_vehiculos`) + códigos de vinculación — R06.
2. Preferencias de notificación por categoría — R11.
3. Reglas/estados de programación de mantenimiento — R08.
4. Coordenadas de sucursales (lat/lng/pin) — R12.
5. Fotografía de perfil — R04.
6. Snapshot de reversa de canje — R06.

## Entidades de Django sin equivalente (conservar, no eliminar)

`analytics`, `api`, `continuity`, `help_center`, `imports`, `leads`, `privacy`, `quality`, `reports`, `sales`, `security_center`, `sri_integration`, `enterprise` — capacidades superiores al original; ninguna debe perderse por el rediseño.

---

# DISEÑO PROPUESTO — R02

Modelos, permisos, migraciones y pruebas por cada fila PENDIENTE de `functional-parity-matrix.md`.

## A. Modelos nuevos propuestos

### A1. `apps.vehicles.VehicleLinkCode` (R06 — F18/F19/F20)
- `vehicle` FK → Vehicle (PROTECT), `code` CharField(19, unique) formato `VNV-XXXX-XXXX-XXXX` generado con `secrets.choice` (alfabeto sin caracteres ambiguos).
- `status` choices: ACTIVO / USADO / REVOCADO (db_index), `created_by` FK User, `expires_at` null, `used_by` FK Customer null, `used_at` null, `revoked_by`, `revocation_reason`.
- Constraint: `UniqueConstraint(fields=["vehicle"], condition=Q(status="ACTIVO"), name="uq_active_link_code_per_vehicle")` → un solo código activo por vehículo (compatible SQLite/PostgreSQL).
- Tests: generación (formato, unicidad), un solo activo, revocación, doble canje rechazado, código revocado rechazado, rate limit del endpoint.

### A2. `apps.vehicles.CustomerVehicle` (R06/R07 — F19/F20/F24/F26)
- `customer` FK Customer, `vehicle` FK Vehicle, `linked_via` FK VehicleLinkCode null, `initial_mileage` PositiveIntegerField null, `is_active` Boolean(db_index), `unlinked_at`, `unlinked_reason`.
- Constraint: `UniqueConstraint(fields=["customer","vehicle"], condition=Q(is_active=True))` → un solo vínculo activo por par; **1 vehículo = 1 dueño activo** (condición `Q(vehicle=...)` imposible con campos fijos → validar en servicio con bloque transaccional).
- Snapshot de reversa: campos desnormalizados (`snapshot_customer_name`, `snapshot_identification`) + AuditLog.
- Tests: doble vinculación rechazada, transferencia de titularidad preserva historial de ServiceOrder, reversa con snapshot.

### A3. `apps.post_sales.MaintenanceRule` (R08 — F28)
- `service_type` Char(40), `interval_km` PositiveIntegerField null, `interval_months` PositiveSmallIntegerField null, `is_enabled` Boolean, `branch` FK Branch null (null = toda la instalación), `description`.
- Cálculo derivado (`next_due_at`/`next_due_km`) en servicio puro `compute_maintenance_status()`, nunca almacenado.
- Tests: cálculo por tipo, fallback por defecto, estados programado/próximo/vencido.

### A4. `apps.notifications.NotificationPreference` (R11 — F47)
- OneToOne → User; campos booleanos por categoría: `in_app_invoice`, `in_app_maintenance`, `in_app_campaign`, `in_app_security`, `email_enabled` (default True).
- Tests: defaults, actualización desde portal, puerta aplicada en eventos (F49).

### A5. `apps.common.ModuleDefinition` (R14 — F52)
- `code` Char(unique), `name`, `is_enabled` Boolean, `config` JSONField, `updated_by`/`updated_at`.
- Migración de datos: crear filas para `post_sales` (respetando el env override actual) y `three_d`.
- `is_module_enabled()` pasa a consultar BD con caché (120 s) + override por settings/env conservado para despliegues.
- Tests: módulo OFF → 404 en URLs, ausente en navbar/search/Assist; env override sigue funcionando.

### A6. Avatar (`apps.accounts.User`)
- `avatar` ImageField(upload_to="avatars/%Y/%m/", blank=True) + `avatar_provider` Char(choices LOCAL/CLOUDINARY, default LOCAL). Implementado en R04.
- Procesamiento: Pillow (decodificación real, max 5 MB, 64²–4096² px, rechazo de bombas de descompresión), guardado vía adaptador A7. **Desviación justificada**: no se recorta a 512² (el diseño inicial lo preveía); se conserva la imagen validada para no imponer encuadre. Render con `components/avatar.html` (imagen o iniciales).
- Migración: `accounts.0003_user_avatar_user_avatar_provider`.
- Tests: subida válida/inválida (tipo falso, >5 MB, dimensiones), sustitución, eliminación → default, presencia en navbar Staff/portal/pública (`apps/accounts/tests/test_avatar.py`, 19 pruebas).

### A7. Adaptador de storage (`apps/accounts/storage.py`)
- `get_avatar_storage()`/`AvatarStorage` según `settings.STORAGE_BACKEND` (`local` default | `cloudinary` si credenciales presentes y SDK instalado; fallback local con aviso). Backend local con `FileSystemStorage` dentro de `MEDIA_ROOT`. Implementado en R04 (el archivo se ubicó en `apps/accounts/` por convivencia del dominio avatar; un adaptador genérico para documentos podrá generalizarse en R12).
- Sin claves en código; documentación de `.env` en `integrations-register.md`.
- Tests: local E2E; cloudinary sin credenciales/SDK degrada a local; ruta cloudinary verificada con SDK simulado (no hay integración real hasta R12).

### A8. Extensiones de modelos existentes
| Modelo | Campos nuevos | Fila | Migración |
|---|---|---|---|
| `ServiceOrder` | `mileage` PositiveIntegerField null, `received_at` DateTime null, `fuel_level` Char(10) blank, `diagnosis` Text blank | F27 | `post_sales.000X_reception_fields` |
| `ServiceOrder` | `void_reason` Char(220) blank, `voided_by` FK User null | F29 | `post_sales.000X_void_fields` |
| `Branch` | `latitude`/`longitude` Decimal(9,6) null, `pin_label` Char(120) blank, `services` JSONField default list, `image_url` URL blank | F41/F43 | `branches.000X_geo_fields` |
| `Customer` | sin campos nuevos (normalización en datos) | F09/F10 | data migration `customers.000X_normalize_identification` |
| `User` | `avatar` + `avatar_provider` (A6) | F25/F44 | `accounts.0003` |

## B. Permisos nuevos (PermissionCode)

| Código | Uso | Roles seed |
|---|---|---|
| `portal.access` | acceso al portal cliente (F24/F26) | cliente |
| `vehicles.link_codes` | generar/revocar códigos (F18/F20) | admin_sucursal, asesor_postventa |
| `post_sales.reception` | recepción y km (F27) | asesor_postventa, admin_sucursal |
| `maintenance.rules` | editar reglas (F28) | admin_sucursal |
| `branches.geo` | editar coordenadas (F43) | admin_sucursal |

Se añaden a `seed_roles.py` con migración de datos (crear PermissionCode si no existe); nunca borrar códigos existentes.

## C. Diseño por fila PENDIENTE (matriz → R02)

| ID | Diseño concreto (modelo / permiso / migración / prueba) | Fase |
|---|---|---|
| F09 | Funciones `validate_ec_cedula`/`validate_ec_ruc` en `common/validators.py` + `clean` en `CustomerForm`; data migration normalizando; test `tests/test_ec_identification.py` | R03 |
| F10 | `normalize_identification()` en `common/normalization.py`; servicio de alta con chequeo difuso (`difflib` ratio ≥0.92) + constraint único ya existente; test dedupe + flujo admin | R03 |
| F11 | AuditLog `action="customer.identification_changed"` con snapshot antes/después en servicios de customers; test de trazabilidad | R03 |
| F15 | Endpoint de edición de identificación con validador + audit; test duplicado rechazado | R03 |
| F18 | Modelo A1 + endpoint bajo `vehicles.link_codes`; test formato/unicidad/revocación | R06 |
| F19 | Modelo A2 + servicio transaccional `redeem_link_code()` con advisory lock; permission `portal.access`; test doble canje | R06 |
| F20 | Revocación A1 + `CustomerVehicle.deactivate()` + snapshot; permiso `vehicles.link_codes`; test reversa | R06 |
| F23 | Vistas públicas `inventory/catalog` con `is_public=True`, agregado booleano de disponibilidad por sucursal (sin costos/stock exacto); sin modelo nuevo; test sin autenticación | R13 |
| F24 | Nueva app `apps/portal` (dashboard, garaje, facturas, documentos, notificaciones, perfil) sobre selectores existentes con ownership filter; `portal.access`; tests de aislamiento por cliente | R07 |
| F25 | Campo A6 + adaptador A7 + vistas de subida/borrado; tests imagen/permisos/render | R04 — IMPLEMENTADO |
| F26 | Vista portal que filtra `ServiceOrder` por `customer`↔`CustomerVehicle`; test "cliente no ve órdenes ajenas" | R09 |
| F27 | Campos A8 en `ServiceOrder` + vista recepción con km/diagnóstico bajo `post_sales.reception`; test recepción y cierre | R08 |
| F28 | Modelo A3 + servicio de cálculo + vista admin de reglas (`maintenance.rules`); test cálculos | R08 |
| F29 | Campos A8 `void_*` + validación ADMIN o autor; test anulación/permiso | R08 |
| F33 | `apps/invoices/pdf.py` con WeasyPrint + plantilla corporativa; storage privado `invoices/`; download view con autorización (emisor o dueño); tests `%PDF` + 403 ajeno | R10 |
| F36 | `ReusableAsset` categoría MANUAL + M2M `vehicle_models` + `is_published`; descarga vía `PrivateDocumentDownloadView`; test publicación/autorización | R09 |
| F39 | Reutiliza F23 (misma vista pública, sección repuestos) | R13 |
| F41 | Campos A8 en `Branch` + página `/ubicaciones/` con lista + mapa MapTiler con fallback sin key; test render sin clave | R13 |
| F42 | Integración MapTiler/MapLibre (cliente) con `MAPTILER_PUBLIC_KEY` en settings; fallback estático; test de contenido con/sin key | R12 |
| F43 | Vista admin selector de coordenadas bajo `branches.geo`; validación rango Ecuador (-5..2, -81..-75) como warning; test validación | R12 |
| F44 | Adaptador A7 con `STORAGE_BACKEND`; documentación de credenciales; tests local + skip cloudinary | R04 — IMPLEMENTADO (integración real en R12) |
| F46 | Endpoint `notifications/mark-all` (POST, CSRF) con ownership por destinatario; test marca solo las propias | R11 |
| F47 | Modelo A4 + vista preferencias en portal; test defaults/persistencia | R11 |
| F49 | `apps/notifications/events.py`: emisión de factura, cierre de orden, canje de código → `create_notification()` respetando A4; tests por evento | R11 |
| F51 | Reorganización de templates públicos (inicio breve + servicios/nosotros/contacto/ubicaciones independientes); rate limit en contacto; tests de rutas y longitud del index | R13 |
| F52 | Modelo A5 + `is_module_enabled()` con caché + nav/search/Assist/vistas protegidos por `OptionalModuleRequiredMixin`; tests módulo OFF | R14 |
| F55 | Reutiliza `VehicleResource` (validadores glb/gltf/usdz ya existentes) bajo módulo `three_d` (A5); UI diferida; test mínimo de módulo OFF | R13/R14 |

## D. Alcance de fases confirmado (R03–R07)

R03 clientes → R04 avatar/storage → R05 búsqueda Staff (COMPLETADA: filtros avanzados, paginación, índices, scoping, anti-enumeración) → R06 garaje/códigos → R07 portal. Las filas F23/F39/F51 (público) se agrupan en R13; F41–F43 en R12/R13; F46/F47/F49 en R11; F27–F29/F28 en R08; F33 en R10; F36 en R09; F52/F54 en R14.
