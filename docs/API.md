# API REST de Vinova Pro

## Versiones

- `/api/`: compatibilidad con endpoints acumulados anteriores.
- `/api/v1/`: contrato recomendado para integraciones nuevas.
- `/api/v1/schema/`: OpenAPI de v1.
- `/api/v1/docs/`: Swagger UI de v1.

En producción la documentación requiere administrador cuando `VINOVA_API_DOCS_PUBLIC=False`.

## Autenticación

La API admite sesión Django para usuarios internos y Bearer Token para integraciones:

```http
Authorization: Bearer vnp_<public_id>.<secreto>
```

El token se muestra una sola vez. Se vincula a un usuario de servicio y puede tener sucursal, vencimiento, allowlist IP y rate limit. La autorización combina alcance API y permiso funcional; ninguno sustituye al otro.

## Administración de integraciones

Solo mediante sesión interna con `integrations.manage`:

```text
GET/POST /api/v1/api-clients/
POST     /api/v1/api-clients/<uuid>/rotate-secret/
POST     /api/v1/api-clients/<uuid>/revoke/
GET      /api/v1/api-scopes/
GET/POST /api/v1/webhook-endpoints/
POST     /api/v1/webhook-endpoints/<uuid>/rotate-secret/
POST     /api/v1/webhook-endpoints/<uuid>/test/
```

Consulta operacional:

```text
GET /api/v1/webhook-events/
GET /api/v1/webhook-deliveries/
POST /api/v1/webhook-deliveries/<uuid>/retry/
GET /api/v1/integration-logs/
```

Un token API no puede administrar credenciales ni secretos, aunque tenga un alcance amplio.

Las APIs privilegiadas también pasan por la política de acceso Staff cuando se
usa autenticación de sesión. Una aprobación adaptativa permite el contexto de
red/sesión, pero nunca concede el scope API ni el permiso funcional faltante.

## Entrada de leads con idempotencia

```text
POST /api/v1/integrations/leads/
Authorization: Bearer ...
Idempotency-Key: <clave única>
Content-Type: application/json
```

Requiere `leads:write` y permisos funcionales de CRM. La misma clave y el mismo cuerpo devuelven la respuesta almacenada; la misma clave con otro cuerpo devuelve conflicto.

## Webhooks

Eventos actuales:

```text
lead.created, lead.updated
sale.created, sale.updated
invoice.created, invoice.updated
vehicle.created, vehicle.updated
integration.test
```

Firma:

```text
X-Vinova-Signature: v1=<HMAC-SHA256>
```

Se firma `<timestamp>.<cuerpo_json_exacto>`. El receptor debe validar además `X-Vinova-Timestamp` y rechazar solicitudes antiguas.

Antes de entregar, VINOVA valida el esquema, resuelve todo el destino DNS y
rechaza cualquier dirección no global salvo una excepción privada explícita.
El transporte conecta a una IP ya aprobada, conserva host/SNI para TLS, no usa
proxy y no sigue redirecciones. Este control reduce SSRF y rebinding dentro de
la aplicación; el filtrado de egreso de infraestructura sigue recomendado.

## BI

Catálogo:

```text
GET /api/v1/bi/
```

Datasets:

```text
GET /api/v1/bi/sales/
GET /api/v1/bi/invoices/
GET /api/v1/bi/inventory/
GET /api/v1/bi/customers/
GET /api/v1/bi/leads/
GET /api/v1/bi/vehicles/
```

Filtros:

```text
start_date=YYYY-MM-DD
end_date=YYYY-MM-DD
updated_since=<ISO-8601>
branch=<id>
limit=1..5000
offset=0..
output=json|csv
```

`customers` y `leads` están diseñados para análisis y no incluyen correo, teléfono, WhatsApp, documento, mensajes ni notas internas.

## Exportación contable

```text
GET /api/v1/integrations/accounting/export/?output=json
GET /api/v1/integrations/accounting/export/?output=csv
```

Contiene información tributaria sensible y exige alcance/permisos específicos. No constituye integración oficial completa con el SRI.

## Endpoints acumulados

El router v1 incluye los recursos construidos previamente: usuarios, roles, empresa, sucursales, vehículos, clientes, inventario, ventas, facturación, documentos, notificaciones, importaciones, empresa avanzada, auditoría, CRM, continuidad, privacidad y seguridad. Cada recurso mantiene sus permisos de negocio y ahora también aplica alcance API y sucursal cuando la autenticación es técnica.

Los archivos privados, backups y exportaciones personales no se sirven desde la API. Sus descargas permanecen en vistas protegidas y auditadas.

## Metadatos

```text
GET /api/v1/meta/
```

Devuelve versión de API/producto, tipo de autenticación y hora del servidor sin exponer secretos.

## API interna de calidad

La automatización QA expone endpoints administrativos bajo `/api/v1/quality/` para consultar ejecuciones y, mediante sesión interna, solicitar un perfil cerrado. No admite autenticación por clientes API, comandos personalizados ni rutas de archivos.

- `GET /api/v1/quality/runs/`
- `GET /api/v1/quality/runs/<uuid>/`
- `POST /api/v1/quality/runs/execute/` con `{ "profile": "quick|full|release" }`

La ejecución requiere el permiso `quality.run`, CSRF válido y el runner QA habilitado. Los reportes completos se descargan desde el panel protegido, no desde una URL pública.
