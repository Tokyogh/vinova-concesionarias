# Integrations register — proveedores verificados

> R01. Proveedores reales identificados en `web_carros/` (referencia) y estado en VINOVA PRO.
> Solo nombres de claves; ningún valor de secreto se registra aquí.

## Proveedores del proyecto original

| # | Proveedor | Uso real | Referencia original | Claves requeridas (nombres) | Exposición | Fallback en original |
|---|---|---|---|---|---|---|
| I1 | **Cloudinary** (`cloudinary==1.44.2`) | ÚNICAMENTE subida de avatar de perfil (300×300, `public_id=usuario_<id>_avatar`, overwrite) | `vinova/core.py:157-164`, `routes/perfil.py:1177-1215` | `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | Server-side | **Ninguno**: si falla, imprime y redirige; no conserva copia local |
| I2 | **MapTiler** + **MapLibre GL JS 4.7.1** (CDN) | Mapa público de instituciones + selector de coordenadas en panel admin; style `dataviz-dark` | `routes/instituciones.py:31`, `routes/admin.py:383`, `templates/instituciones.html:404`, `static/js/instituciones.js:18`, `static/js/admin.js:760` | `MAPTILER_KEY` | **Clave visible en HTML/JS del navegador** (por diseño) | Sí: `showFallback` sin clave (`instituciones.js:395-404`) |
| I3 | **SMTP** (genérico) | Correo transaccional: contacto, reset, registro, factura, mantenimiento, canje, alta de usuario | `core.py:237-369` | `EMAIL_MODE`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USE_TLS`, `SMTP_USE_SSL`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME`, `CONTACT_EMAIL`, `PASSWORD_RESET_MINUTES` | Server-side | **Sí**: `EMAIL_MODE=simulado` (default) imprime en consola |
| I4 | **WeasyPrint 69.0** (local, no API) | Generación de PDF de facturas con `templates/factura_pdf.html` + `factura_pdf.css` | `services/facturas.py:127-145` | — (requiere pango/MSYS2 en Windows: `iniciar_windows.ps1`) | — | Sí: PDF manual crudo (`services/facturas.py:148-240`), calidad limitada |

Claves adicionales leídas por código con defaults: `MAX_UPLOAD_MB`, `LOGIN_MAX_ATTEMPTS`, `LOGIN_WINDOW_SECONDS`, `LOGIN_LOCK_SECONDS`, `TRUST_PROXY_HEADERS`, `PRIVATE_STORAGE_ROOT`, `DATABASE_PATH`.

**No existen** en el original: S3/boto3, Supabase, Firebase, imgbb, Google Maps JS API, Leaflet, OpenLayers, WhatsApp/chat/push.

## Estado en VINOVA PRO (Django)

| Proveedor | Estado actual | Evidencia | Plan |
|---|---|---|---|
| Cloudinary / storage externo | **ADAPTADOR LISTO (R04)**: `apps/accounts/storage.py` resuelve `STORAGE_BACKEND`; local por defecto, Cloudinary solo con SDK + `CLOUDINARY_*`; fallback local con aviso. SDK `cloudinary` no instalado (se añadirá en R12 con credenciales reales) | `config/settings/base.py`, `apps/accounts/storage.py`, `apps/accounts/cloudinary_avatar.py`, `apps/accounts/tests/test_avatar.py` | R12: instalar SDK, probar subida real y documentar cuotas/restringir claves |
| Mapas | **NO EXISTE** (0 coincidencias leaflet/mapbox/google en templates/static; `Branch` sin lat/lng; Permissions-Policy bloquea geolocalización) | grep en `templates/`, `static/`, `apps/` | R12: añadir lat/lng a `Branch`, integrar MapTiler (mismo proveedor real) con fallback sin clave |
| SMTP | **EXISTE** (backend de correo Django configurable) | `config/settings/` | R12: verificar configuración y plantillas HTML |
| PDF | **NO EXISTE** (sin librería PDF; salida actual = vista imprimible HTML) | `requirements/base.txt`, `apps/invoices/views.py:184` | R10: elegir WeasyPrint o ReportLab y añadir a requirements; storage privado ya existe (`documents/storage.py`) |
| SRI | Estructura preparada sin emisión (`sri_integration`) | `apps/sri_integration/models.py` | No tocar (fase SRI específica requerida) |

## Reglas

- No inventar proveedores: los únicos candidatos de mapa/storage son los verificados arriba (o alternativas documentadas explícitamente).
- No exponer secretos; las claves solo en `.env`/settings. La clave de mapa del cliente se considera pública pero debe restringirse por dominio.
- Si faltan credenciales: documentar configuración y continuar con alternativa local segura (mismo criterio que el original: fallback simulado/local).
