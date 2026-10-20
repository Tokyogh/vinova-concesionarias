# Módulos y feature flags

La instalación es single-tenant: una organización por despliegue. Los feature flags son globales para esa instalación.

## Postventa

`VINOVA_MODULE_POST_SALES_ENABLED=False` por defecto.

Al activarlo se habilitan navegación, vistas, servicios y notificaciones de órdenes de postventa. Desactivado no bloquea ventas, inventario ni el resto del núcleo.

## Backups automáticos

`VINOVA_AUTOMATED_BACKUPS_ENABLED=False` por defecto. Active solo después de validar almacenamiento, cola Celery, política de retención y restauración.

## QA empresarial

- `VINOVA_QA_EXECUTION_ENABLED=False`: bloquea ejecuciones desde panel y API.
- `VINOVA_QA_AUTOMATED_ENABLED=False`: bloquea programación automática.

QA usa infraestructura y base aisladas; nunca debe apuntar a la base empresarial.

## SRI

El módulo SRI es preparatorio y permanece en estado `NOT_CONFIGURED` sin credenciales. No emite comprobantes automáticamente ni es requisito para operar Vinova Pro.

Todo cambio de flags debe probarse primero en staging y acompañarse de `docker compose exec web python manage.py check`.
