# B9 — Presentación profesional

Fecha de cierre: 2026-10-15

## Alcance revisado

Se buscaron nombres demostrativos, vehículos ficticios presentados como reales, marcas provisionales, texto temporal y errores de codificación en templates, formularios, vistas, servicios y contenido de ayuda activos. No se modificaron registros de clientes, cuentas, vehículos ni datos persistentes.

## Hallazgos y correcciones

- Se corrigió mojibake visible en el flujo interno de campañas: títulos, estados, validaciones, mensajes de éxito y denegaciones vuelven a mostrar correctamente caracteres como `ñ`, `ó`, `í`, `é` y el separador `·`.
- Se reparó el docstring dañado del catálogo público de vehículos.
- Los fallbacks internos de fotografía y descripción del vehículo ahora usan estados neutrales (`Sin imagen principal`, `Sin descripción comercial`, `Sin descripción ampliada`) en lugar de presentarlos como contenido futuro.
- La portada pública muestra `Ubicación no especificada` cuando una sucursal activa no tiene ciudad, en lugar de `Ciudad por definir`.
- Se añadió una migración declarativa para sincronizar las etiquetas corregidas de `Campaign.Status`, `Campaign.SegmentType` y `Campaign.Channel`; no transforma filas ni modifica valores almacenados.
- Se añadió regresión automática contra marcadores habituales de mojibake y branding demostrativo en superficies activas.

## Contenido conservado deliberadamente

- Los comandos `seed_demo_*` permanecen porque son fixtures sintéticos explícitos para entornos locales; no se ejecutaron ni se modificaron sus datos.
- Los ejemplos de formato (`VNV-XXXX-XXXX-XXXX`, rangos, referencias y placeholders de búsqueda) son ayudas de entrada, no información empresarial ficticia.
- Los estados operativos `Pendiente`, `Por definir`, `Temporal` o `Pruebas` se conservaron cuando describen un estado real del flujo, como una fecha de servicio aún no asignada o un entorno de validación.
- La vista previa de campañas conserva la indicación de que renderiza con el primer destinatario real del segmento calculado.

## Validaciones

- Barrido de fuentes activas: 0 líneas con marcadores de codificación sospechosos.
- `makemigrations --check --dry-run`: sin deriva después de la migración.
- `manage.py check`: 0 incidencias.
- Ruff y compilación Python: aprobados.
- Compilación de 201 templates Django: aprobada.
- Pruebas focales de UI, campañas, catálogo público y portada: 36 aprobadas.

## Resultado

Las interfaces activas no contienen branding “Vinova Demo” ni texto ficticio presentado como dato real. Los únicos datos demostrativos continúan aislados en seeds explícitos y no se creó información persistente.
