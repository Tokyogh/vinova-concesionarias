# Configuración de Vinova Pro 2.0.0

Parta de `.env.example` para desarrollo, `.env.staging.example` para staging y `.env.production.example` para producción. Los archivos `.env` reales nunca deben versionarse.

## Núcleo

- `SECRET_KEY`: secreto estable y único.
- `DEBUG`: siempre `False` en producción.
- `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS`: dominios explícitos.
- `DATABASE_URL`: PostgreSQL de la instalación.
- `REDIS_URL`, `CELERY_BROKER_URL` y `CELERY_RESULT_BACKEND`: Redis y Celery.
- `VINOVA_HEALTHCHECK_HOST`: host admitido para probes internos.

## Seguridad e integraciones

- `VINOVA_API_TOKEN_PEPPER`: secreto HMAC independiente; rotarlo invalida tokens API.
- `VINOVA_API_CLIENT_DEFAULT_RATE`: límite predeterminado de clientes API.
- `VINOVA_IDEMPOTENCY_TTL_HOURS`: retención de respuestas idempotentes.
- `VINOVA_WEBHOOK_ALLOW_PRIVATE_NETWORKS`: mantener `False` en producción.
- `VINOVA_API_DOCS_PUBLIC`: mantener `False` en producción.
- `VINOVA_MAX_UPLOAD_MB`: debe concordar con `NGINX_CLIENT_MAX_BODY_SIZE`.
- `VINOVA_ZIP_MAX_ENTRIES`, `VINOVA_ZIP_MAX_UNCOMPRESSED_MB` y
  `VINOVA_ZIP_MAX_COMPRESSION_RATIO`: límites previos a extracción para ZIP/Office.
- `VINOVA_IMPORT_MAX_ROWS` y `VINOVA_IMPORT_MAX_COLUMNS`: límites de trabajo para CSV/XLSX.
- `VINOVA_ARCHIVE_MAX_MEMBERS` y `VINOVA_ARCHIVE_MAX_UNCOMPRESSED_MB`: límites para
  backups y paquetes de transferencia; dimensionarlos con la capacidad real.
- `VINOVA_PUBLIC_FORM_MAX_SUBMISSIONS` y `VINOVA_PUBLIC_FORM_WINDOW_SECONDS`: límites de formularios públicos.
- `VINOVA_PUBLIC_PARTS_CATALOG_ENABLED`: habilita o bloquea navegación y URL del catálogo público de repuestos.
- `VINOVA_COOKIE_CONSENT_NAME` y `VINOVA_COOKIE_CONSENT_AGE`: nombre y vigencia de la preferencia firmada; producción exige prefijo `__Host-`.

## HTTPS, proxy y servidor

- `SECURE_SSL_REDIRECT` y `SECURE_HSTS_SECONDS`.
- `VINOVA_TRUST_PROXY_HEADERS`: habilitar solo detrás de un proxy controlado.
- `NGINX_TLS_ENABLED`, `NGINX_SERVER_NAME`, certificados y proxy CIDR.
- `GUNICORN_WORKERS`, `GUNICORN_THREADS`, timeouts y `max_requests`.

## Correo, storage y observabilidad

- Variables `EMAIL_*` para SMTP.
- `STORAGE_BACKEND=local|cloudinary` controla avatares. Cloudinary requiere
  `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY` y `CLOUDINARY_API_SECRET`.
- `PRIVATE_STORAGE_BACKEND=local|s3` controla documentos sensibles. S3-compatible
  requiere endpoint, access key, secret, bucket y región; genera URL firmada con
  expiración y cifra objetos con AES-256 del proveedor.
- `PRIVATE_STORAGE_ROOT` sigue siendo el fallback local. Seleccionar un backend
  externo incompleto hace fallar el readiness y la verificación estricta.
- `SENTRY_DSN`, entorno, release y sample rate.
- `LOG_LEVEL` y `DJANGO_LOG_LEVEL`.

## Automatización controlada

- `VINOVA_AUTOMATED_BACKUPS_ENABLED`: activar únicamente tras probar política, almacenamiento y restore.
- `VINOVA_QA_EXECUTION_ENABLED` y `VINOVA_QA_AUTOMATED_ENABLED`: desactivadas por defecto.
- `CELERY_BACKUP_QUEUE`, `CELERY_WEBHOOK_QUEUE` y `CELERY_QA_QUEUE`: colas dedicadas.

## Políticas administradas en la aplicación

`SecurityPolicy` mantiene la política de contraseñas/sesiones y el acceso Staff
`off|monitor|enforce`, incluidas CIDR confiables y ventanas de solicitud y
aprobación. No se configura por una variable de entorno para evitar cambios
opacos sin validación ni auditoría. `enforce` requiere red confiable y otro
aprobador global activo con 2FA; el valor inicial es `off`.

Las categorías de cookies opcionales son `preferences`, `analytics` y
`external_content`. El servidor bloquea su uso antes del renderizado cuando la
cookie firmada no concede la categoría; una bandera frontend no sustituye este
control.

Consulte [Módulos](MODULOS.md) para feature flags y los archivos `.env.*.example` para la lista ejecutable vigente.
