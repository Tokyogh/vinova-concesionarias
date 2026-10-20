# Testeo beta — índice maestro

Estas guías describen pruebas manuales sobre funciones reales de VINOVA PRO. No contienen resultados de personas, credenciales ni datos empresariales. Cada ejecución debe hacerse sobre una copia de la plantilla y custodiarse fuera del repositorio si incluye nombres, firmas o evidencia sensible.

## Reglas de ejecución

1. Use un entorno local, QA o staging autorizado; nunca producción para mutaciones.
2. Registre entorno, commit, navegador, dispositivo y rol antes del primer caso.
3. Use datos sintéticos identificables y dos sucursales cuando el caso compruebe alcance.
4. No cambie permisos para hacer pasar un caso. Registre la denegación real.
5. Estados permitidos: `pendiente`, `aprobado`, `fallido`, `bloqueado`, `no aplica`.
6. Adjunte evidencia sin contraseñas, tokens, cédulas completas ni archivos privados.
7. Un proveedor, TLS o staging no disponible se marca `bloqueado`; no se simula como aprobado.
8. En estas guías, “alcance” significa ver únicamente la sucursal o expediente permitido; “acceso horizontal” significa intentar abrir datos de otra persona o sede.
9. Mantenga cada caso en `pendiente` hasta que una persona ejecute todos sus pasos y adjunte evidencia segura.

### Palabras técnicas usadas en algunos casos

- permiso API (también llamado *scope*): operación concreta que puede pedir una integración;
- interruptor de módulo (también llamado *feature flag*): opción que enciende o apaga una función completa;
- acceso a datos propios (también llamado *ownership* en evidencia técnica): una cuenta solo puede abrir sus registros;
- contenido enviado (también llamado *payload*): datos que viajan en una solicitud;
- hash: huella no reversible usada para comprobar integridad, no el secreto original.

## Artefactos maestros

- [Matriz de trazabilidad](testeo-matriz-trazabilidad.md)
- [Plantilla individual de ejecución](testeo-plantilla-ejecucion.md)
- [Plantilla de incidencia](testeo-plantilla-incidencia.md)
- [Consolidación de resultados](testeo-consolidacion-resultados.md)
- [Correcciones F17](testeo-correcciones-f17.md)

## Guías por rol

| Rol oficial | Guía |
|---|---|
| `superadmin` | [Superadministración](testeo-rol-superadmin.md) |
| `admin_general` | [Administración general](testeo-rol-admin-general.md) |
| `admin_sucursal` | [Administración de sucursal](testeo-rol-admin-sucursal.md) |
| `gerente_comercial` | [Gerencia comercial](testeo-rol-gerente-comercial.md) |
| `jefe_inventario` | [Jefatura de inventario](testeo-rol-jefe-inventario.md) |
| `vendedor` | [Ventas](testeo-rol-vendedor.md) |
| `asesor_postventa` | [Asesoría de postventa](testeo-rol-asesor-postventa.md) |
| `facturacion` | [Facturación](testeo-rol-facturacion.md) |
| `bodega` | [Bodega](testeo-rol-bodega.md) |
| `marketing` | [Marketing](testeo-rol-marketing.md) |
| `soporte_cliente` | [Soporte al cliente](testeo-rol-soporte-cliente.md) |
| `auditor` | [Auditoría](testeo-rol-auditor.md) |
| `cliente` | [Cliente](testeo-rol-cliente.md) |

## Guías por módulo o flujo

| Cobertura | Guía |
|---|---|
| autenticación, cuentas, 2FA, sesiones y acceso Staff fuera de red | [Cuentas y seguridad](testeo-modulo-cuentas-seguridad.md) |
| empresa, sucursales, foto/website, instituciones, mapa consentido y portal público | [Empresa, sedes y público](testeo-modulo-empresa-sucursales-publico.md) |
| expedientes, asociación segura, datos propios y portal | [Clientes y portal](testeo-modulo-clientes-portal.md) |
| inventario vehicular, publicación, multimedia y códigos | [Vehículos](testeo-modulo-vehiculos.md) |
| artículos, stock, movimientos, transferencias y catálogo público de repuestos | [Inventario](testeo-modulo-inventario.md) |
| leads, pipeline, cotización, reserva y venta | [CRM y ventas](testeo-modulo-crm-ventas.md) |
| comprobantes, pagos, anulaciones, PDF y archivos privados | [Facturación y documentos](testeo-modulo-facturacion-documentos.md) |
| órdenes, historial, mensajes, preferencias y campañas | [Postventa y notificaciones](testeo-modulo-postventa-notificaciones.md) |
| reportes, exportaciones, BI, analítica e importaciones | [Reportes, analítica e imports](testeo-modulo-reportes-analitica-imports.md) |
| cookies, consentimiento, solicitudes, export, anonimización y eventos | [Privacidad y auditoría](testeo-modulo-privacidad-auditoria.md) |
| API, webhooks, scopes, backups, restore y transferencias | [Integraciones y continuidad](testeo-modulo-integraciones-continuidad.md) |
| módulos ON/OFF, QA, ayuda, responsive y errores | [Calidad, ayuda y configuración](testeo-modulo-calidad-ayuda-configuracion.md) |
| validación de contacto, VNV, vehículo, ayuda, responsive y mapas F17 | [Correcciones F17](testeo-correcciones-f17.md) |

## Exclusiones y gates

No probar como funcionalidad habilitada: SRI operativo, recordatorios automáticos de mantenimiento, importación histórica LITE, SaaS o multiempresa. Proveedores externos reales, DNS/TLS, almacenamiento productivo, restauraciones reales, revisión legal y aprobación visual humana son gates separados.
