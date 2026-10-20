# Mapas funcionales de VINOVA PRO

Fecha de generación: 2026-10-19

Escenario automatizado: `tests/e2e/test_12_functional_maps.py`

Entorno: servidor Django temporal, base de datos E2E aislada y Chromium controlado

## Alcance y garantías

Estas capturas documentan interfaces reales de VINOVA PRO. El escenario crea únicamente datos sintéticos en la base temporal de pruebas, abre las rutas reales y comprueba respuesta HTTP 200, presencia de los componentes señalados y ausencia de desbordamiento horizontal del documento. Los círculos numerados y la leyenda se agregan temporalmente antes de cada captura; no forman parte de la interfaz entregada al usuario.

La evidencia no contiene credenciales, tokens, claves de proveedores ni datos personales reales. La captura de instituciones habilita medios externos mediante una preferencia temporal de cookies y ejercita el mapa configurado; si el proveedor no está disponible, la aplicación conserva su fallback controlado.

## Recorridos documentados

| Evidencia | Ruta real | Propósito |
|---|---|---|
| [01 — Dashboard cliente](capturas/01-dashboard-cliente.png) | `/mi-cuenta/` | Resumen privado del expediente, vehículos, servicios y actividad. |
| [02 — Indicadores de mantenimiento](capturas/02-indicadores-mantenimiento.png) | `/mi-cuenta/` | Órdenes abiertas, próximas atenciones y serie mensual. |
| [03 — Perfil cliente](capturas/03-perfil-cliente.png) | `/mi-cuenta/perfil/` | Datos de cuenta y contacto editables bajo validación. |
| [04 — Mis vehículos](capturas/04-mis-vehiculos.png) | `/mi-cuenta/vehiculos/` | Garaje limitado a las vinculaciones activas del cliente. |
| [05 — Vinculación por código](capturas/05-vinculacion-codigo.png) | `/mi-cuenta/vehiculos/agregar/` | Canje VNV privado sin solicitar kilometraje al cliente. |
| [06 — Historial de servicios](capturas/06-historial-servicios.png) | `/mi-cuenta/servicios/?view=history` | Órdenes no borrador asociadas a vehículos propios. |
| [07 — Documentos](capturas/07-documentos.png) | `/mi-cuenta/documentos/` | Documentos privados activos autorizados. |
| [07b — Facturas](capturas/07b-facturas.png) | `/mi-cuenta/facturas/` | Comprobantes no borrador del expediente. |
| [08 — Notificaciones](capturas/08-notificaciones.png) | `/mi-cuenta/notificaciones/` | Mensajes enviados al cliente o a su cuenta. |
| [09 — Instituciones y mapa](capturas/09-instituciones-mapa.png) | `/instituciones/` | Sedes públicas, filtros, mapa y panel de detalle. |
| [10 — Dashboard Staff](capturas/10-dashboard-staff.png) | `/dashboard/admin/` | Perfil operativo, indicadores y acciones resueltas por RBAC. |
| [11 — Inventario](capturas/11-inventario.png) | `/dashboard/inventory/` | Existencias, mínimos y movimientos bajo alcance de sucursal. |
| [12 — Ventas](capturas/12-ventas.png) | `/dashboard/sales/` | Pipeline y operaciones comerciales accesibles. |
| [13 — Administración de vehículo](capturas/13-administracion-vehiculo.png) | `/dashboard/vehicles/<id>/` | Identidad, estado, multimedia, ficha, garaje y códigos. |
| [14 — Ayuda contextual](capturas/14-ayuda-contextual.png) | `/dashboard/help/` | Búsqueda y biblioteca filtradas por publicación y permisos. |

## Lectura técnica

- [Portal cliente](01-portal-cliente.md): ownership, cálculos, documentos, facturas y notificaciones.
- [Instituciones públicas](02-instituciones-publicas.md): publicación, coordenadas, filtros y proveedor cartográfico.
- [Operación Staff](03-operacion-staff.md): dashboard, inventario, ventas y administración vehicular.
- [Ayuda y método de evidencia](04-ayuda-y-metodo.md): visibilidad, versionado, permisos y reproducción.

## Reproducción

El escenario se ejecuta con el perfil E2E de Chromium:

```powershell
.\scripts\qa-e2e.ps1 maps chromium
```

El runner conserva artefactos técnicos en `private/qa_reports/`; las imágenes aprobadas de esta documentación se escriben en `docs/mapas-funcionales/capturas/`. No debe ejecutarse contra producción ni con información empresarial real.
