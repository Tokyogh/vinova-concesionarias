# R03 — Clientes e identificación (informe de fase)

**Fase:** R03 · **Estado:** COMPLETADA · **Iniciativa:** VINOVA_PRO_FUNCTIONAL_REDESIGN

## 1. Referencia original investigada

`web_carros/vinova/core.py:1077-1179` (validadores módulo 10/11), `routes/trabajador.py:784-956` (alta/edición con dedupe), `routes/facturas.py:99` y `routes/perfil.py:736` (actualizaciones silenciosas sin auditoría — no copiadas).

## 2. Funcionalidades implementadas

- **Validadores EC** en `apps/common/validators.py`: `is_valid_ec_cedula`, `is_valid_ec_ruc`, `validate_ec_cedula`, `validate_ec_ruc` (provincia 01–24, tercer dígito, módulo 10, módulo 11 público/privado, rechazo de repetidos y `…000`).
- **Normalización** en `apps/common/normalization.py`: `normalize_identification()` (strip + separadores) e `identification_digits()`.
- **Módulo `apps/customers/identification.py`**: validación por tipo, normalización para almacenamiento (cedula/RUC → solo dígitos), duplicado exacto, candidatos difusos (SequenceMatcher ≥ 0.92, sin fusión automática) y helper de data migration.
- **Aplicación transversal**: `Customer.clean()` (cubre formulario y API), `Customer.save()` (normalización defensiva), `CustomerForm.clean()` (validación + duplicado + `fuzzy_candidates`), avisos no bloqueantes en las vistas de alta/edición.
- **Auditoría**: acción `customers.identification_change` con snapshot antes/después, `severity=medium`, `is_sensitive=True` en `update_customer` y `update_customer_from_data`.
- **Data migration** `customers/0002_normalize_identification_data` (no destructiva: solo normaliza sin colisión).

## 3. Diferencias justificadas

- La identificación **no** es clave primaria; se conserva el constraint único parcial existente.
- Pasaporte/Otro no se validan como EC (la referencia solo valida cédula/RUC); sí se deduplican.
- Candidatos difusos generan **aviso**, nunca fusión automática.

## 4. Modelos/migraciones

Sin cambios de esquema; 1 data migration (`customers/0002`). `makemigrations --check` → sin cambios detectados.

## 5. Seguridad y permisos

Validación siempre en backend (modelo, formulario y servicios); permisos existentes `customers.manage` sin cambios; auditoría sensible.

## 6. Pruebas ejecutadas

- `python manage.py check` → OK.
- `pytest apps/common/tests/test_ec_identification.py apps/customers` → **56 passed**.
- Suite completa `-m "not e2e"` → **2214 passed, 2 skipped, 5 failed** = exactamente los 5 fallos preexistentes de R00 (2 × `test_d5_privilege_escalation` públicas, 3 × `test_conversion_concurrency_v110` SQLite locking).
- `ruff check` en archivos modificados → limpio.
- Test DB reconstruida con `--create-db` (migración aplicada) → OK.

## 7. Fallos pendientes

Los 5 preexistentes de R00 (no relacionados con esta fase).

## 8. Commit local

`R03: customer identification - EC validators, normalization, dedupe, audit` (más informe y checkpoint).

## 9. Próxima fase y punto de reanudación

- **Siguiente:** R04 — Fotografías de perfil: campo `User.avatar`, adaptador de storage (`STORAGE_BACKEND`, local + Cloudinary opcional), subida/edición/borrado con validación Pillow, avatar en navbar Staff/portal/pública.
- **Reanudar en:** diseño `data-model-map.md` §A6/§A7 + filas F25/F44 de la matriz.
