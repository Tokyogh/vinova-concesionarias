# Decisions — arquitectura y negocio

> Registro de decisiones de VINOVA PRO FUNCTIONAL REDESIGN. R00–R01 base.

## R00

1. **Repositorio único**: continuar en `feature/v0-2-auth-roles`; no crear proyecto nuevo.
2. **`web_carros/` solo lectura**: excluido de git vía `.git/info/exclude`; nunca commitear ni migrar su BD.
3. **AGENTS.md único y depurado**: se fusionaron y deduplicaron encabezados; reglas permanentes intactas; checkpoint conservado (sección 4).
4. **Checkpoint conservador**: `PUSH_AUTHORIZED: NO`, `VISUAL_APPROVED: NO`, `FINAL_HUMAN_REVIEW: PENDING` durante toda la hoja de ruta.
5. **Baseline con pruebas preexistentes**: 5 fallos conocidos documentados (2 en `test_d5_privilege_escalation.py` de páginas públicas, 3 en `test_conversion_concurrency_v110.py`); no se atribuyen a esta iniciativa.
6. **Single-tenant sin excepción**: ninguna fase puede introducir multi-tenancy.

## R01

7. **Auditoría por bloques con subagentes**: los 8 ámbitos de R01 se auditaron en paralelo sobre `web_carros/` y se volcaron en `reference-inventory.md` con referencias `archivo:línea`.
8. **Referencia funcional es Flask, no Django**: se adopta la lógica de negocio, no la arquitectura (sin SQLAlchemy/raw SQL en el código nuevo; usar ORM y migraciones Django).
9. **Identidad del vehículo**: conservar `vin`+`internal_code` de VINOVA PRO; la referencia no tiene VIN (usa `codigo_catalogo`+placa) → no degradar el modelo actual.
10. **Cédula/RUC**: no usar identificación como clave primaria; módulo 10/11 se porta como validador (R03), manteniendo separación cuenta↔expediente.
11. **Storage**: único candidato externo verificado = Cloudinary (solo avatares en referencia); se implementará adaptador con fallback local (R04/R12). No se evalúan proveedores nuevos sin evidencia.
12. **Mapas**: se conserva MapTiler/MapLibre (proveedor real de la referencia), con fallback sin clave. Coordenadas reales de sucursales, nunca inventadas.
13. **PDF**: WeasyPrint es la referencia funcional; librería final por decidir en R10 (WeasyPrint vs ReportLab) según despliegue; storage privado ya existente en VINOVA PRO.
14. **Módulos**: la referencia es monolítica; se diseña matriz ON/OFF configurable (R14) sin romper módulos actuales.
15. **No copiar debilidades**: lista `S1–S22` de `reference-inventory.md` §13; cada nueva implementación debe superar la referencia, no reproducirla.

## R02

16. **Garaje = tabla `CustomerVehicle`**, no campo en `Vehicle`: un vehículo puede cambiar de titular sin destruir historial; historial técnico (`ServiceOrder`) nunca se traslada al nuevo dueño.
17. **Códigos de vinculación = `VehicleLinkCode`** con constraint parcial (un código ACTIVO por vehículo), generación con `secrets`, revocación y snapshot de reversa; la cédula sola nunca prueba propiedad.
18. **Vinculación transaccional**: canje con `transaction.atomic` + advisory lock (`common/db_locks.py`); sin doble canje posible.
19. **Portal = nueva app `apps/portal`** (no ramificar `accounts`): módulo OPCIONAL con `portal.access`, reutilizando selectores existentes con ownership filter.
20. **Avatar en `User` con adaptador de storage**: `STORAGE_BACKEND` local por defecto; Cloudinary solo si hay credenciales; nunca hardcodear secretos; sin fallback silencioso roto (advertencia + guardado local).
21. **Validadores ecuatorianos en `common/validators.py`**: cédula/RUC como funciones puras con tests propios; `identification_number` sigue sin ser clave primaria.
22. **Deduplicación por servicio + constraint**: unicidad exacta en BD (ya existe) + chequeo difuso en alta; nunca fusión automática de expedientes con conflictos.
23. **Identificación auditada**: cualquier cambio de cédula/RUC genera `AuditLog` con snapshot antes/después; prohibidas las actualizaciones silenciosas.
24. **Postventa ampliada, no recreada**: `ServiceOrder` gana recepción (km, fecha, combustible, diagnóstico) y anulación con motivo; se conserva `ServiceOrderHistory`.
25. **Reglas de mantenimiento configurables** (`MaintenanceRule`) en lugar de tabla hardcodeada; cálculo derivado sin persistir estado derivado.
26. **PDF de factura con WeasyPrint** (referencia real) + plantilla corporativa; storage privado ya existente en `documents`; autorización obligatoria en descarga; numeración ya única en VINOVA PRO (no copiar la débil de la referencia).
27. **Manuales como `ReusableAsset` publicable por modelo de vehículo**, descargables solo con autorización (nunca enlaces estáticos públicos como la referencia).
28. **Mapas: conservar MapTiler/MapLibre** (proveedor verificado) con clave pública restringible por dominio y fallback estático sin clave; coordenadas reales en `Branch`, nunca inventadas.
29. **Módulos configurables en BD (`ModuleDefinition`)** manteniendo el override env actual para despliegues; módulo OFF = 404 + ausencia en navbar/search/Assist (no solo CSS).
30. **F55 (preview 3D)**: reutilizar `VehicleResource` (ya valida glb/gltf/usdz) bajo módulo `three_d`; sin rediseño de UI en esta iniciativa.
31. **Orden de fases confirmado**: R03 clientes → R04 avatar/storage → R05 búsqueda → R06 garaje → R07 portal; público (F23/F39/F51) en R13; integraciones (F41–F43) en R12/R13.
32. **Avatar en `User`**: `ImageField(upload_to="avatars/%Y/%m/")` + `avatar_provider` (LOCAL/CLOUDINARY) con migración `accounts.0003`; se conserva la identidad del usuario y no se crea modelo separado.
33. **Adaptador de storage con degradación segura**: `STORAGE_BACKEND=local` usa `FileSystemStorage` dentro de `MEDIA_ROOT`; `cloudinary` solo se usa con el SDK instalado y las tres credenciales presentes, de lo contrario fallback local con `warning` (nunca error de subida). No se añade `cloudinary` a requirements hasta R12.
34. **Validación real de avatar con Pillow**: formato JPEG/PNG/WEBP, tamaño (`VINOVA_AVATAR_MAX_MB`=5), dimensiones (`64`–`4096`), verificación de decodificación y rechazo de bombas de descompresión; archivos ejecutables o con contenido falso se rechazan aunque la extensión sea válida.
35. **Permisos de avatar**: cada usuario gestiona únicamente su propio avatar (subida/sustitución/eliminación); el avatar se muestra en navbar Staff, navbar pública autenticada, perfil y ficha de usuario, con iniciales como respaldo.
36. **Sustitución limpia**: al reemplazar el avatar se elimina el archivo anterior tras guardar el nuevo; los proveedores externos usan `overwrite=True` y `get_available_name` determinista para no generar nombres alternativos.
37. **Búsqueda Staff R05 sobre los listados internos existentes**: no se crea una nueva app; se amplían `CustomerSearchForm`/`VehicleSearchForm` y sus selectores con campos explícitos (cédula/RUC, nombres, apellidos, correo, teléfono, placa, VIN, sucursal, estado; en vehículos: VIN, placa, código interno, marca, modelo).
38. **Cédula/RUC en búsqueda**: se normaliza a dígitos y, si es un documento EC válido (10/13 dígitos), se usa coincidencia exacta indexada; de lo contrario coincidencia parcial con mínimo de 6 dígitos para no enumerar la base.
39. **Anti-enumeración**: longitud mínima en texto libre (2) y por campo (identificación 6, teléfono 6, placa 3, VIN 6) con límite de longitud (80); la paginación (20/página) y el scoping por sucursal son la segunda barrera; las consultas usan ORM y whitelist de ordenamiento.
40. **Placas tolerantes a separadores**: el filtro de placa normaliza mayúsculas y admite cualquier carácter no alfanumérico entre dígitos (`iregex`), de modo que `ABC-1234` y `ABC1234` se encuentren mutuamente sin cambiar el formato almacenado.
41. **N+1 cubierto por pruebas**: la vaciado de la página (20 filas) se resuelve en 1 consulta principal en clientes (≤3 con scope) y en ≤5 en vehículos (scope + 2 prefetch) verificados con `CaptureQueriesContext`.
42. **Contrato de accesibilidad actualizado**: `test_customer_search_filters_have_accessible_names` ahora refleja el conjunto completo de filtros R05 y exige `aria-label` + `form-control` en cada campo.
