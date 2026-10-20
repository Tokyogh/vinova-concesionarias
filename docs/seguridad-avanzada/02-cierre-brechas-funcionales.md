# F2 — cierre de brechas funcionales

Fecha: 2026-10-15

## Sedes e instituciones

Se añadieron `photo` y `website_url` a `Branch` mediante una migración aditiva. El formulario administrativo acepta imágenes JPG/PNG/WEBP validadas por contenido y tamaño, y URLs limitadas a HTTP/HTTPS con HTTPS asumido cuando se omite el esquema.

El servicio de creación/edición conserva transacciones y registra en auditoría el nombre de almacenamiento de la imagen y la URL. El directorio público solo refleja estos campos cuando la sede y su empresa están activas y la sede está marcada como pública. Los enlaces externos usan `noopener noreferrer`.

La imagen por categoría se mantiene como fallback, de modo que no se requieren registros ficticios ni una fotografía obligatoria.

## Catálogo público de repuestos

Se añadió `/repuestos/` reutilizando `InventoryItem`, `InventoryCategory` y `BranchStock`:

- solo publica artículos activos, no eliminados y marcados explícitamente con `is_public`;
- limita el catálogo a bienes físicos: aceites, filtros, repuestos, accesorios y otros;
- permite búsqueda, categoría, tipo, orden, limpieza de filtros y paginación;
- muestra imagen, descripción, código y precio de venta;
- informa únicamente disponibilidad cualitativa y nombres de sedes activas/públicas;
- excluye costo, cantidades, reservas, mínimos, proveedor, ubicación y movimientos;
- rechaza filtros manipulados sin ampliar la consulta;
- se desactiva completamente con `VINOVA_PUBLIC_PARTS_CATALOG_ENABLED=False`, incluida la navegación.

La interfaz replica la jerarquía de LITE con tarjetas, filtros y modal, empleando tokens de color PRO, HTML semántico, cierre por teclado nativo y responsive.

## Archivos y controles

- Migración: `branches.0004_branch_photo_branch_website_url`.
- Backend: validación contextual, selector de proyección pública y 404 cuando el módulo está OFF.
- Frontend: escape de plantillas, sin construcción de HTML dinámico y JavaScript limitado a diálogos.
- Auditoría: snapshots de altas y modificaciones de sedes.
- Privacidad comercial: ninguna cifra de stock ni costo llega al contexto renderizado.

## Verificación

- Django check: aprobado.
- Drift de migraciones: ninguno.
- Ruff focal: aprobado.
- Compileall y `node --check`: aprobados.
- Regresión completa `branches` + `inventory`: 30 pruebas aprobadas.
- `diff --check`: limpio.
- `web_carros/`: sin cambios.

La carga real de multimedia mediante el proveedor productivo y la revisión visual humana permanecen como gates externos.
