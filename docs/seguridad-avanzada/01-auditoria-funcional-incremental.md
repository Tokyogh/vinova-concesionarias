# F1 — auditoría funcional incremental

Fecha: 2026-10-15
Base revisada: `9f04aaf`

## Método y alcance

Esta fase reutiliza el inventario, la matriz de paridad y las 2.470 pruebas del cierre B12. Entre esa base y el inicio de F1 no hubo cambios funcionales versionados; por ello se revisaron los deltas conocidos y sus recorridos completos, sin repetir la auditoría general.

Se contrastaron modelos, formularios, servicios, selectores, vistas, rutas, plantillas, JavaScript y pruebas de `branches` e `inventory`, además de su exposición en el shell público. `web_carros/` se consultó exclusivamente como referencia.

## Resultado por capacidad prioritaria

| Capacidad | Estado observado | Evidencia | Clasificación |
|---|---|---|---|
| creación y edición de sedes | implementada | `BranchForm`, servicios transaccionales y pruebas CRUD/auditoría | verificada en B12 |
| publicación de sedes | implementada | `is_active`, `is_public` y selector público | verificada en B12 |
| coordenadas, mapa y filtros | implementada | rangos de modelo, MapLibre y filtros con limpieza | verificada en B12 |
| servicios y horarios por sede | implementada | `services`, `opening_hours` y representación pública | verificada en B12 |
| fotografía configurable por sede | ausente | el modelo no tiene campo y la página usa imágenes estáticas por categoría | defecto de paridad confirmado |
| sitio web por sede | ausente | no existe campo, validación ni enlace público | defecto de paridad confirmado |
| catálogo interno de inventario | implementado | artículos, categorías, imagen, precio, stock, movimientos y permisos | verificada en B12 |
| datos aptos para publicación | parciales | `InventoryItem` ya posee `is_public`, imagen, descripción y precio | base reutilizable |
| catálogo público de repuestos | ausente | no existe ruta, selector ni plantilla pública | defecto de paridad confirmado |
| disponibilidad pública segura | ausente | existe stock por sede, pero no una proyección pública que oculte cantidades | defecto funcional confirmado |
| configuración ON/OFF del catálogo público | ausente | inventario no posee flag público independiente | control requerido |

## Recorrido extremo a extremo esperado para F2

### Sedes

Interfaz administrativa → validación de URL/imagen → servicio transaccional → persistencia y auditoría → selector público → tarjeta/detalle público. Una sede inactiva o no pública no debe aparecer; una imagen inválida no debe guardarse; el enlace externo debe usar esquema permitido y apertura segura.

### Repuestos

Formulario interno existente → `is_public` y estado activo → selector público de solo lectura → búsqueda/filtros/paginación → tarjeta/modal responsive. La salida puede informar disponibilidad general y sedes con unidades disponibles, pero no cantidades, stock mínimo, reservas, costo, proveedor, ubicación interna ni movimientos.

## Áreas sin nuevo defecto demostrado

El código funcional no cambió desde B12 en cuentas/2FA, clientes, vehículos, CRM, ventas, facturación, documentos, notificaciones, reportes, portal, integraciones y operación. Sus estados permanecen respaldados por el informe B12. Las fases F3–F12 volverán sobre controles de seguridad, entradas, privacidad, dependencias y disponibilidad; esto no equivale a declarar que carecen de riesgo residual.

## Decisiones acotadas

- No se añade proveedor, marca ni reserva comercial porque PRO no tiene una política de exposición aprobada para esos datos.
- El precio público usa únicamente `InventoryItem.price`, ya identificado como precio de venta; nunca `cost`.
- La disponibilidad se expresará por estado y nombres de sedes públicas, sin cifras.
- El catálogo se habilitará con un flag explícito y seguro, sin convertir inventario en módulo SaaS.

## Próximo bloque

Implementar las cuatro brechas confirmadas con migración, validación contextual, auditoría, navegación pública y pruebas de no exposición.
