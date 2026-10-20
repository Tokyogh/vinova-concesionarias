# Arquitectura

Cada app debe separar: `models.py`, `views.py`, `forms.py`, `services.py`, `selectors.py`, `permissions.py`, `api/`, `tests/` y `docs/`.

## Roles múltiples

Un usuario puede tener varios roles al mismo tiempo y esos roles pueden ser globales o por sucursal. Esto evita depender de un rol genérico llamado trabajador.

Roles base: superadmin, admin_general, admin_sucursal, gerente_comercial, jefe_inventario, vendedor, asesor_postventa, facturacion, bodega, marketing, soporte_cliente, auditor y cliente.

## Vehículos

El vehículo soporta galería de fotos, modelo 3D opcional, fallback visual cuando no hay 3D, recursos reutilizables y especificaciones por partes con imagen propia.

## CRM y analítica

`apps/leads/` contiene modelos, formularios, selectores, servicios, vistas, API, pruebas y comando demo del pipeline comercial.

`apps/analytics/` conserva interacciones del catálogo y genera agregados comerciales. La lógica de lectura está separada en selectores y no modifica ventas ni leads.

Flujo principal:

```text
Catálogo público → Lead → Seguimiento/Test drive → Cliente → Cotización/Venta → Analítica
```

## Topología de producción

Nginx es el único servicio expuesto. Web, PostgreSQL, Redis, Celery Worker y Celery Beat comparten una red interna. `app_init` ejecuta una sola vez checks, migraciones y collectstatic. El volumen privado no se monta en Nginx.


## API, integraciones y BI

`apps/api/` actúa como frontera de integración. Separa autenticación, permisos, alcance por sucursal, servicios de idempotencia, tareas webhook, datasets y vistas internas. Los tokens API se vinculan a usuarios de servicio y nunca sustituyen los permisos de negocio.

Flujo de entrada:

```text
Sistema externo → APIClient → alcance + permiso + sucursal → idempotencia → servicio de negocio → auditoría/log
```

Flujo de salida:

```text
Cambio de negocio → señal mínima → WebhookEvent → Celery/webhooks → entrega HMAC → reintento/log
```

Los datasets BI son contratos de lectura versionados; no consultan una base paralela ni introducen multi-tenancy.


## Ayuda y capacitación

`apps/help_center/` mantiene separados los contenidos formativos de la lógica operativa. Los artículos y checklists se cargan mediante un seed idempotente, se filtran por permisos y roles y se asocian a nombres de URL reales para ayuda contextual. El progreso pertenece a cada usuario y los cambios relevantes se auditan. Las copias Markdown viven en `docs/manuals/`.

## Capas y límites

- `views.py`/`api/views.py`: frontera HTTP, método, autenticación y permiso;
- `forms.py`/serializers: tipos, formatos, relaciones y choices autorizadas;
- `selectors.py`: querysets con sucursal, ownership y estados visibles;
- `services.py`: mutaciones, transacciones, locks, auditoría y efectos secundarios;
- `models.py`: relaciones, constraints y estado persistente;
- `tasks.py`: trabajo asíncrono idempotente y acotado.

La UI nunca es una frontera de seguridad. Ocultar un botón no reemplaza el
permiso en vista/servicio, y conocer un ID no evita el selector scoped.

## Configuración modular

Los módulos opcionales se resuelven en backend y navegación. Cuando postventa
está OFF, GET, POST y URL directa responden 404. Los flags no deben dejar tareas,
exports o APIs laterales activas.

El catálogo público de repuestos reutiliza `InventoryItem`, `InventoryCategory`
y `BranchStock`; no crea un inventario paralelo. Su selector proyecta solo
campos públicos y disponibilidad cualitativa, y el flag
`VINOVA_PUBLIC_PARTS_CATALOG_ENABLED` bloquea navegación y URL directa.

## Perímetros de seguridad y privacidad

El middleware de acceso Staff evalúa red, sesión y una señal mínima de
navegador antes de paneles y APIs privilegiadas. Los modos `off`, `monitor` y
`enforce` viven en `SecurityPolicy`; una excepción es temporal, contextual,
auditada y requiere otra cuenta de rango superior con 2FA y
`security.approve_staff_access`. No asigna roles ni reemplaza RBAC.

Las tecnologías opcionales siguen un gate previo al renderizado:

```text
petición → cookie firmada/versionada → categoría permitida
         → contexto mínimo → JavaScript/proveedor opcional
```

Sin consentimiento no se renderizan MapTiler/MapLibre ni se registra analítica
de catálogo. Sesión y CSRF siguen siendo tecnologías necesarias y conservan
sus controles independientes.

## Datos y archivos

PostgreSQL 16 es el motor operativo. Redis soporta caché, throttling y Celery.
Los documentos privados no están bajo el árbol público de media; las descargas
pasan por autorización y auditoría. S3-compatible y Cloudinary son adaptadores
opcionales con fallback controlado, no requisitos implícitos.

Los validadores inspeccionan contenido y contenedores antes de persistir. ZIP,
Office, CSV/XLSX y TAR de continuidad tienen límites configurables de miembros,
filas, columnas y expansión; esto reduce agotamiento de recursos, pero no
sustituye el antivirus/CDR pendiente para archivos externos.

Detalle: [base de datos](BASE_DATOS.md), [API](API.md) y
[estado actual](ESTADO_ACTUAL.md).
