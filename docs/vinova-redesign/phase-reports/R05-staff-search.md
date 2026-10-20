# R05 — Búsqueda empresarial Staff

- **Fase:** R05 · **Estado:** COMPLETADA y validada (suite completa en verde salvo 5 fallos preexistentes de R00).
- **Referencia original:** `web_carros/perfil.py:532-647`, `services/notificaciones.py:151-217` (búsquedas AJAX LIMIT 30/25 sin scoping).
- **Commit local:** al cierre de la fase.

## Implementado

1. `apps/common/search.py` (nuevo): `clean_search_query`/`clean_name_query`/`clean_identification_query`/`clean_phone_query`/`normalize_plate`/`normalize_vin`/`plate_startswith_q`. Mínimos y máximos de longitud para proteger contra consultas masivas y de enumeración.
2. Búsqueda de clientes (`CustomerSearchForm` + `customer_list_queryset`): campos explícitos `identification` (cédula/RUC normalizada, exacta si es documento EC válido, parcial ≥6 dígitos si no), `first_name`, `last_name`, `email`, `phone`, `plate`, `vin` (a través de `CustomerVehicleInterest.vehicle`), además de `q`, `status`, `customer_type`, `branch`, `sort`. `distinct()` al buscar por vehículo.
3. Búsqueda de vehículos (`VehicleSearchForm` + `internal_vehicle_queryset`): `vin`, `plate`, `internal_code`, `brand`, `model` (selects buscables), además de `q`, `status`, `branch`, `sort`.
4. Permisos reales mantenidos: `customers.view`/`customers.manage`, `vehicles.view`/`manage`/`publish` con fallback gestionar; scoping por sucursal de `apps/accounts/scopes.py` aplicado antes de cada filtro (sin filtración horizontal).
5. Rendimiento: `select_related` en ramas, `prefetch_related("media","highlights")` en vehículos; índices existentes reutilizados (`identification_number`, `plate`, `vin`, `status`, `branch`, `email`, `phone`).
6. Plantillas: los paneles de filtro muestran los nuevos campos en la sección "Más filtros" (`advanced`).
7. Tests (26 nuevos): `apps/customers/tests/test_staff_search.py` (9), `apps/vehicles/tests/test_staff_search.py` (9), `apps/common/tests/test_search_helpers.py` (8). Cubren cédula/RUC exacta y parcial, nombre, apellidos, correo, teléfono, placa, VIN, marca, modelo, combinaciones, paginación, permisos (403/302), aislamiento por sucursal, mínimo de longitud y ausencia de N+1 (`CaptureQueriesContext`). Se actualizó el contrato de accesibilidad `test_customer_search_filters_have_accessible_names`.

## Diferencias justificadas

- El original no aplicaba scoping por sucursal ni longitud mínima; aquí sí (seguridad por diseño).
- Las placas se buscan tolerando separadores (`iregex`) sin alterar el formato almacenado.
- No se agregaron índices nuevos: los existentes cubren los patrones de consulta (la búsqueda parcial de placa es puntual y acotada a 20 filas/página).

## Modelos / migraciones

- Ninguno nuevo en R05; `python manage.py check` OK y `makemigrations --check` sin cambios.

## Seguridad y permisos

- Backend autoritativo (ORM/querysets parametrizados, sin SQL concatenado).
- Anti-enumeración: mínimos de longitud por campo y `q`, máximo 80 caracteres, whitelist de ordenamiento.
- Sin filtración entre sucursales: los filtros se aplican siempre después del scope.

## Pruebas

- `apps/{customers,vehicles,common}`: **220 passed / 1 skipped**.
- Suite completa: **2262 passed / 33 skipped / 6 failed** — los 6 fallos = 5 preexistentes de R00 (2× `test_d5_privilege_escalation`, 3× `test_conversion_concurrency_v110`) + 1 error transitorio de bloqueo SQLite en ejecución completa (resuelto al ejecutar el test aislado; el contrato de accesibilidad actualizado pasa solo).
- `python manage.py check`: sin problemas. `makemigrations --check`: sin cambios. `ruff check`: limpio.

## Fallos pendientes

- Nada nuevo en R05. Los 5 fallos preexistentes de R00 se mantienen sin regresión.

## Próxima fase

- R06 — Vehículos y garaje digital: modelo A1 `VehicleLinkCode` (códigos VNV-XXXX…), modelo A2 `CustomerVehicle`, canje/reversa transaccional, vinculación segura por código privado, historial de propietarios y archivado.

## Punto de reanudación

- Reanudar en `apps/vehicles/` + `apps/customers/` para R06: diseñar `VehicleLinkCode`/`CustomerVehicle` (sección A1/A2 de `data-model-map.md`), generación `secrets.choice` 16 B, canje con advisory lock (`apps/common/db_locks.py`), permisos `vehicles.link_codes`, tests de doble canje/reversa.