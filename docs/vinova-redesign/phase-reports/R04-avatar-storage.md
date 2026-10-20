# R04 — Fotografías de perfil (avatar y storage) (informe de fase)

**Fase:** R04 · **Estado:** COMPLETADA · **Iniciativa:** VINOVA_PRO_FUNCTIONAL_REDESIGN

## 1. Referencia original investigada

`web_carros/vinova/core.py:157-164` (config Cloudinary), `routes/perfil.py:1177-1243` (POST `/perfil/foto`: validación cliente ≤25 MB, subida Cloudinary `usuario_<id>_avatar`, sin fallback), `static/js/script1.js` (validación de tipo/tamaño).

## 2. Funcionalidades implementadas

- **Campos**: `User.avatar` (`ImageField`, `upload_to="avatars/%Y/%m/"`, `storage=AvatarStorage`, validación) y `User.avatar_provider` (LOCAL/CLOUDINARY) — migración `accounts.0003`.
- **Adaptador de storage** (`apps/accounts/storage.py`): `STORAGE_BACKEND=local` → `FileSystemStorage` en `MEDIA_ROOT`; `cloudinary` → solo con SDK instalado y credenciales `CLOUDINARY_*` presentes (`apps/accounts/cloudinary_avatar.py`), si no fallback local con `warning`. Sin secretos en código.
- **Validación real con Pillow** (`apps/common/validators.py::validate_avatar_image`): formato JPEG/PNG/WEBP, tamaño ≤5 MB (`VINOVA_AVATAR_MAX_MB`), dimensiones 64–4096 (`VINOVA_AVATAR_MIN/MAX_DIMENSION`), decodificación verificada y bombas de descompresión; contenido falso se rechaza aunque la extensión sea válida.
- **Vistas y URLs** (`accounts.avatar_update`, `accounts.avatar_delete`): subida, sustitución, edición y eliminación del propio avatar; el archivo anterior se elimina tras guardar el nuevo.
- **Render** (`templates/components/avatar.html`): imagen o iniciales como respaldo, en navbar Staff (`base.html`), navbar pública autenticada (`public.html`), perfil (`accounts/profile.html` con formulario de gestión) y ficha de usuario (`accounts/user_detail.html`). CSS `.avatar` en `static/css/ui/components/brand.css`.

## 3. Diferencias justificadas

- No se fuerza recorte a 512² (el diseño A6 lo preveía): se conserva la imagen validada. Documentado en `data-model-map.md` §A6.
- El adaptador vive en `apps/accounts/` (dominio avatar) y no en `apps/common/storage.py`; un adaptador genérico se evaluará en R12.
- Cloudinary no se instala todavía (no hay credenciales ni cuotas verificadas); su ruta se prueba con SDK simulado y queda para integración real en R12.

## 4. Modelos/migraciones

`accounts/0003_user_avatar_user_avatar_provider` (dos campos, no destructiva). `makemigrations --check` sin cambios pendientes.

## 5. Seguridad y permisos

Solo el usuario autenticado gestiona su propio avatar (vistas operan `request.user`); subida anónima redirige a login. Validación siempre en backend (modelo + formulario). Sin secretos versionados; fallback local seguro.

## 6. Pruebas ejecutadas

- `python manage.py check` → OK; `ruff check` → limpio.
- `pytest apps/accounts/tests/test_avatar.py` → **19 passed** (validación, subida, sustitución, borrado, permisos, render, resolución de storage).
- `pytest apps/accounts apps/customers apps/common` → **226 passed, 1 skipped**.
- Suite completa `-m "not e2e"` → **2237 passed, 2 skipped, 5 failed** = exactamente los 5 fallos preexistentes de R00 (2 × `test_d5_privilege_escalation` públicas, 3 × `test_conversion_concurrency_v110` SQLite locking). No hay regresiones nuevas.

## 7. Fallos pendientes

Los 5 preexistentes de R00 (ajenos a esta fase).

## 8. Commit local

`R04: user avatar - validated upload, storage adapter, navbar rendering`.

## 9. Próxima fase y punto de reanudación

- **Siguiente:** R05 — Búsqueda empresarial Staff (cédula/RUC, nombre, correo, teléfono, placa, VIN, sucursal, estado; filtros, paginación, índices, permisos, protección contra consultas masivas).
- **Reanudar en:** `functional-parity-matrix.md` filas F12–F14 y `data-model-map.md` §C.
