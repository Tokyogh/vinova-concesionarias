# F17.5–F17.7 — Canje y administración de vehículos

Fecha: 2026-10-18

## Contrato VNV verificado

El emisor de `VehicleLinkCode` ya configurado en PRO genera cuatro grupos de cuatro caracteres con un alfabeto sin símbolos ambiguos:

`VNV-XXXX-XXXX-XXXX-XXXX`

La referencia de tres grupos visible en formularios y documentación provenía de LITE y no coincidía con los códigos emitidos por PRO. No se modificó el algoritmo ni ningún código existente. La entrada ahora:

- admite pegado con o sin guiones;
- convierte a mayúsculas y segmenta mientras se escribe;
- limita el tamaño a 23 caracteres;
- conserva edición y navegación por teclado;
- valida en backend el prefijo, los cuatro grupos y el alfabeto real;
- mantiene expiración, estado, unicidad, bloqueo y consumo atómico.

## Canje sin kilometraje del cliente

- Los dos endpoints de canje dejaron de leer o enviar `mileage` al servicio.
- `redeem_link_code` toma únicamente el kilometraje administrado del vehículo.
- `Vehicle.mileage` admite `NULL` para representar “no registrado”; no se convierte en cero.
- Un canje legítimo no se bloquea por kilometraje ausente.
- La ficha Staff y el portal muestran “No registrado” cuando corresponde.
- Los valores heredados se conservan; la migración no reescribe datos existentes.

## Administración ampliada

El formulario principal ya cubría todos los campos escalares ordinarios de `Vehicle`. F17 añadió gestión autorizada para relaciones existentes, sin crear modelos duplicados:

- metadatos y visibilidad de `VehicleMedia`, con desvinculación que conserva el recurso reutilizable;
- destacados de `VehicleCommercialHighlight`;
- características y especificaciones de `VehiclePartSpecification`, incluido JSON estructurado e imagen reutilizable;
- validación de controles invisibles, límites y alcance de sucursal;
- auditoría para crear, actualizar y eliminar/desvincular.

VIN, marca, modelo y año se consideran identidad técnica. Modificarlos exige justificación, se registra en auditoría y está prohibido cuando el vehículo está reservado o vendido. `internal_code`, ownership, ventas, reservas, facturas e historial no son editables desde este formulario.

## Evidencia

- Regresión focal: 58 aprobadas, 1 omitida existente.
- Regresión completa de vehículos y portal: 113 aprobadas, 3 omitidas.
- Django check y drift de migraciones: aprobados.
- Ruff, compileall y sintaxis de 7 archivos JavaScript: aprobados.
