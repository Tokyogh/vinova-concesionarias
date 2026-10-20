# B3 — Flujos empresariales de extremo a extremo

Fecha: 2026-10-15
Commit funcional: `e7bd0ed`
Resultado focal: **154 passed, 3 skipped**.

## Instituciones y sucursales

### Recorrido verificado

```text
Rol global con branches.manage
  → /dashboard/branches/new/
  → BranchForm (normalización y rangos)
  → create_branch()/update_branch() atómicos
  → Branch en PostgreSQL
  → AuditLog before/after
  → public_institution_queryset()
  → /instituciones/
  → data-lat/data-lng
  → MapLibre + MapTiler o fallback seguro
```

| Paso | Evidencia | Resultado |
|---|---|---|
| Acceso | `GlobalBranchAccessMixin` requiere `branches.manage` global; usuario autenticado sin permiso obtiene 403. | **VERIFICADO** |
| Interfaz | Formulario interno incluye empresa, nombre, código, tipo, ciudad, provincia, dirección, contacto, descripción, horario, servicios, coordenadas, publicación y estado. | **VERIFICADO** |
| Validación | ModelForm valida tipos/rangos; servicios se separan, deduplican y limitan; API exige lista y normaliza. | **VERIFICADO** |
| Servicio | Alta y edición usan servicios transaccionales; no hay escritura directa desde las vistas HTML/API. | **VERIFICADO** |
| Auditoría | Alta y edición registran snapshots completos. Se corrigió que el snapshot previo del ModelForm ya mutado fuera falso: ahora se recarga y bloquea la fila persistida. | **CORREGIDO / VERIFICADO** |
| Persistencia | La prueba crea una institución sintética de Quito, comprueba servicios y coordenadas, edita ubicación y vuelve a consultar. | **VERIFICADO** |
| Publicación | Solo empresa activa + Branch activa, pública y de tipo permitido llega al directorio; bodegas y privadas quedan fuera. | **VERIFICADO** |
| Mapa | El HTML publica coordenadas no localizadas; JS valida rango, crea marker y actualiza encuadre/popup. Sedes sin coordenadas siguen en lista. | **VERIFICADO** localmente |
| Filtros | Select, búsqueda, tarjetas con toggle y “Limpiar filtros”; URL sincronizada. | **VERIFICADO** por E2E previo y regresión vigente |
| Desactivación | Editar `is_active=False` elimina la sede de la publicación sin borrar el registro. | **VERIFICADO** |
| Fotografía/website | No hay campos ni storage por sede; se muestran assets de categoría. | **BRECHA DE PRODUCTO P2**; no se improvisa sin diseño de almacenamiento y exposición. |

Las coordenadas no se autocompletan por coincidencia textual ni se inventan. El seed demo es idempotente y solo corresponde a entornos no productivos.

## Flujos intermodulares

| Flujo | Interfaz → servicio → persistencia → resultado | Controles | Evidencia B3 |
|---|---|---|---|
| Cuenta → Customer → portal | Invitación/registro o asociación explícita → servicios cliente → `Customer.account` → resolución del dashboard. | Cuenta/rol activos, vigencia de `portal.access`, Customer elegible; Staff no se convierte implícitamente. | `test_client_access`, preparación QA y suite portal. **VERIFICADO** |
| Vehículo → código → garaje | Staff genera código → `generate_vehicle_link_code` → Customer canjea → `CustomerVehicle` activo. | Permiso `vehicles.link_codes`, branch scope, advisory lock, expiración, único owner y auditoría. | `test_garage`. **VERIFICADO** |
| Desvincular/transferir vehículo | Vista interna → servicio con row lock → vínculo anterior inactivo + snapshot → nuevo vínculo. | Solo branch autorizado; historial técnico no se reasigna indebidamente. | `test_garage`. **VERIFICADO** |
| Lead → Customer → cotización | Pipeline/acciones → servicios Lead/Sale → Customer y SaleRecord. | Permisos separados, branch scope, validación de estados y transacción. | suites leads/sales; concurrencia PG queda para B12. **VERIFICADO** |
| Venta → factura → PDF | Venta vendida → `create_invoice_from_sale` → InvoiceRecord/líneas/aplicaciones → impresión/PDF privado. | `sales.sell`, `invoices.issue`, secuencia, Decimal, ownership y `no-store`. | suites sales/invoices/portal. **VERIFICADO** |
| Servicio → historial cliente | Staff crea/actualiza orden → servicios post_sales → historial → portal filtra no borradores propios. | Flag ON/OFF, permisos Staff, branch scope y ownership CustomerVehicle. | suites post_sales/portal. **VERIFICADO** |
| Notificación → destinatario → bandeja | Compose/evento → NotificationMessage/Recipient → bandeja Customer/User. | Scope, deduplicación, consentimiento, CSRF; marcar todas solo toca destinatarios propios. | portal notifications. **VERIFICADO** |
| Configuración → módulo ON/OFF | Setting → `is_module_enabled`/mixin/contexto → navegación, consulta y mutación. | OFF devuelve 404 incluso por URL directa; servicio no genera órdenes. | optional-module y portal service tests. **VERIFICADO** |
| Inventario → movimiento → stock | Formulario → `record_stock_movement`/`transfer_stock` → BranchStock + ledger. | Row locks, no negativo, reservas comerciales, permisos en cada sucursal. | inventory suites. **VERIFICADO** |
| Stock → reposición | Detalle del artículo → formulario por fila → `update_minimum_stock` → BranchStock + AuditLog. | `inventory.manage_stock`, queryset scoped y revalidación del servicio. Sucursal ajena obtiene 404. | Nueva regresión B3. **CORREGIDO / VERIFICADO** |

## Correcciones realizadas

### B3-01 — Snapshot previo de Branch incorrecto

`ModelForm.full_clean()` muta `form.instance` antes de `form_valid()`. `update_branch()` tomaba el estado “antes” desde esa instancia y podía registrar coordenadas/dirección nuevas como si fueran previas. La solución bloquea y lee nuevamente la fila persistida con `select_for_update()` antes de guardar. La prueba demuestra valores diferentes en `AuditLog.before` y `after`.

### B3-02 — Servicio de reposición sin interfaz

`BranchStockSettingsForm` y `update_minimum_stock()` existían, pero ninguna URL o vista los consumía. Se añadió una mutación POST desde el detalle del artículo, campos accesibles por sucursal, mensajes controlados y prueba negativa horizontal. No se duplicó lógica ni se abrió un endpoint global.

## Validación ejecutada

- Django `check`: PASS.
- Ruff focal: PASS.
- Sucursales + inventario: **24 passed** después de las correcciones.
- Matriz cruzada de branches, cuenta cliente, garaje, ventas, facturación, portal, módulos e inventario: **154 passed, 3 skipped**.
- `web_carros/`: sin cambios.

## Riesgos y pendientes

- Imagen y website por sede requieren una decisión de producto y diseño seguro de storage; no son un parche de integración.
- Catálogo público de repuestos continúa como desarrollo P3 separado.
- Entrega real de SMTP/Celery, proveedores de archivos y despliegue permanecen gates externos.
- Los skips condicionados y la concurrencia PostgreSQL se consolidan en B12.

## Cierre B3

Los recorridos prioritarios conectan interfaz, autorización, servicio, persistencia y resultado observable. B3 se cierra **COMPLETADO CON DOS DEFECTOS PUNTUALES CORREGIDOS** y dos capacidades de producto documentadas sin expansión no autorizada.
