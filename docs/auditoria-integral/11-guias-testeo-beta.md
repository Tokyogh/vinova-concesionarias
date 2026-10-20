# B11 — Guías de testeo beta

Fecha de cierre: 2026-10-15

## Entregables

Se creó `docs/testeo-beta/` con 30 documentos, todos bajo el prefijo `testeo-`:

- 13 guías de rol, una por cada rol oficial de `seed_roles`;
- 12 guías modulares que cubren los dominios y flujos reales del inventario;
- índice maestro, matriz de trazabilidad, plantilla de ejecución, plantilla de incidencia y procedimiento de consolidación.

## Cobertura

- 78 casos de rol: acceso, navegación, operación permitida, denegación directa, sucursal/ownership, sesión, ayuda y responsive.
- 136 casos modulares: autenticación, 2FA, empresa/sedes/mapa, clientes/portal, vehículos, inventario, CRM/ventas, facturas/documentos, postventa/notificaciones, reportes/analítica/imports, privacidad/auditoría, API/continuidad y QA/configuración.
- 214 IDs únicos y estables en total.
- Cada caso define módulo, precondiciones, pasos numerados, resultado esperado, resultado obtenido vacío, estado inicial `pendiente`, evidencia y observaciones.
- Las guías separan funciones maestras de resultados humanos; no contienen aprobaciones, firmas ni datos de evaluadores ficticios.

## Seguridad y límites

Las instrucciones exigen datos sintéticos, entornos no productivos, evidencia redactada y dos sucursales/clientes para negativos de aislamiento. SRI operativo, recordatorios automáticos, histórico LITE, SaaS y multiempresa permanecen excluidos. TLS, proveedores, restore real, revisión legal y aprobación visual humana se registran como gates externos.

## Validaciones documentales

- 30/30 nombres cumplen prefijo `testeo-`.
- 25/25 guías de rol/módulo contienen objetivo, requisitos, casos, checklist, incidencias/observaciones y conformidad.
- 13/13 roles oficiales tienen guía y seis casos propios.
- Los 12 prefijos modulares de la matriz de trazabilidad tienen todos sus casos definidos.
- Enlaces locales del conjunto: 0 rotos.
- Los estados de ejecución permanecen sin resultados humanos inventados.

## Uso

La entrada canónica es [`testeo-indice-maestro.md`](../testeo-beta/testeo-indice-maestro.md). Cada evaluador trabaja sobre una copia de la plantilla; el procedimiento de consolidación agrega resultados sin incorporar identidad sensible al repositorio.
