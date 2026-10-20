# Mapa funcional — Operación Staff

## Dashboard adaptable

Evidencia: [10-dashboard-staff.png](capturas/10-dashboard-staff.png)

`dashboard_manifest_for_user` obtiene roles y permisos activos, resuelve un perfil con `dashboard_profile_for_user` y filtra widgets y acciones contra permisos reales y módulos ON/OFF antes de aplicar el orden preferido. Ser `is_staff` no sustituye un `PermissionCode`. El panel administrativo agrega indicadores desde los modelos de compañías, sedes, usuarios, vehículos, clientes, ventas, documentos, notificaciones, facturas, leads y analítica; las acciones solo enlazan operaciones que el manifiesto autorizó.

Sin datos, los indicadores son cero y las listas recientes quedan vacías. Sin una capacidad requerida, el widget o acción no se incorpora. Las vistas destino vuelven a exigir su permiso, por lo que ocultar un enlace no es la defensa principal.

## Inventario

Evidencia: [11-inventario.png](capturas/11-inventario.png)

| Área | Fuente y cálculo | Permisos y mutación | Estado vacío / prueba |
|---|---|---|---|
| Indicadores | `inventory_metrics`: artículos activos/archivados, suma de `BranchStock.quantity`, existencias bajo mínimo, sedes con stock y movimientos confirmados. | `inventory.view` permite lectura; cambios de stock requieren `inventory.manage_stock` y servicios transaccionales. | Ceros controlados. Pruebas contrastan alcance HTML/API y denegación entre sucursales. |
| Artículos | `inventory_item_queryset`: `InventoryItem` no borrados, stock total, número de sedes y existencia de mínimos bajos. | CRUD y archivo pasan por vistas/servicios del dominio. | Filtros sin coincidencia muestran tabla vacía. |
| Movimientos | `stock_movements_queryset`: `StockMovement` con artículo, origen, destino, creador y orden por confirmación. | Entradas, salidas, ajustes y transferencias verifican todas las sedes afectadas; no permiten stock negativo. | El alcance usa `accessible_branch_ids`; no se expone un movimiento de otra sede. |

## Ventas

Evidencia: [12-ventas.png](capturas/12-ventas.png)

`accessible_sales_queryset` aplica `scope_queryset_to_user_branches` con `sales.quote`, `sales.reserve` y `sales.sell`. `sales_metrics` calcula operaciones abiertas, cotizadas, reservadas, ventas e ingresos del mes, saldos pendientes y pagos confirmados. `sale_list_queryset` busca sobre número, cliente y vehículo dentro del alcance ya autorizado; después aplica estado, tipo, sede y orden.

Las transiciones comerciales se ejecutan en servicios transaccionales y requieren el permiso específico. Un resultado vacío no amplía el alcance. Las pruebas cubren creación de cotización, reserva, confirmación, inventario reservado/deducido y aislamiento de sucursal.

## Administración de vehículo

Evidencia: [13-administracion-vehiculo.png](capturas/13-administracion-vehiculo.png)

| Componente | Fuente | Operaciones | Control |
|---|---|---|---|
| Identidad y ficha | `Vehicle`, `VehicleBrand`, `VehicleModel`, sede, estado, VIN, placa, código interno y datos comerciales. | Crear/editar mediante `VehicleForm`, `create_vehicle` y `update_vehicle`. Cambios de identidad sensibles exigen motivo. | `vehicles.manage`, selector por sucursal y auditoría antes/después. |
| Multimedia | `VehicleMedia` y recurso asociado. | Cargar, editar metadatos y desvincular mediante servicios específicos. | Tipo/tamaño del upload, `vehicles.manage`, ownership de la relación y auditoría. |
| Destacados y especificaciones | `VehicleCommercialHighlight` y `VehiclePartSpecification`. | Crear, editar y quitar desde formularios relacionados. | El objeto se obtiene a través del vehículo ya acotado; no se acepta una relación de otro vehículo. |
| Publicación y estado | `Vehicle.status`, `is_public`, `is_featured`. | Publicar, ocultar o archivar por servicios de estado. | `vehicles.publish`, validación de transición y mensajes controlados. |
| Garaje y códigos | `CustomerVehicle` y `VehicleLinkCode`. | Generar/revocar VNV, desvincular o transferir titularidad conservando historial técnico. | `vehicles.link_codes`, cliente destino dentro del alcance, razón limitada y operación auditada. |

La captura reveló que la plantilla usaba un nombre de clase responsive inexistente en dos tablas. F17 sustituyó esas referencias por el contenedor `responsive-table` ya definido; la prueba visual confirma que el documento no desborda a 1440 px sin alterar los controles de acceso.
