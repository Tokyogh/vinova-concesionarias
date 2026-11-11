# Estado actual de VINOVA PRO

Fecha de revisión documental: 2026-11-11. Rama comercial: `main`.

## Implementado

- arquitectura Django modular con portal público, portal cliente y operación Staff;
- operación monocompañía con alcance por sucursal, RBAC, vigencia y ownership;
- CRM, vehículos, inventario, ventas, facturación interna, documentos,
  notificaciones, reportes, privacidad, auditoría y API;
- controles de CSRF, XSS, IDOR, archivos, sesiones, 2FA, rate limiting,
  trazabilidad y almacenamiento privado;
- Docker Compose, QA aislado, backups, restore drills y smoke documentados;
- manuales operativos, mapas funcionales y guías de testeo beta por rol y módulo.

El detalle verificable se mantiene en [Funcionalidades](FUNCIONALIDADES.md),
[Arquitectura](ARQUITECTURA.md), [Roles y permisos](ROLES_PERMISOS.md) y
[Testing](TESTING.md).

## Límites y riesgos abiertos

- no es SaaS ni multi-tenant;
- no existe integración fiscal operativa con el SRI;
- no incluye recordatorios automáticos de mantenimiento;
- postventa permanece deshabilitada por defecto;
- antivirus/CDR externo, filtrado de egreso, vault/HSM y un sink de auditoría
  externo e inmutable siguen siendo mejoras de infraestructura;
- capacidad, RPO/RTO y retención requieren métricas del entorno real.

## Gates externos

- staging, DNS y TLS;
- proveedores reales de correo, storage, mapas, observabilidad y webhooks;
- restauración medida sobre infraestructura candidata y smoke posterior;
- revisión jurídica de privacidad, retención y licenciamiento;
- aprobación visual y beta humana.

## Veredicto

La distribución puede evaluarse en una beta controlada. No está certificada
para producción y ningún resultado local sustituye los gates externos ni una
nueva ejecución de pruebas sobre el commit candidato.
