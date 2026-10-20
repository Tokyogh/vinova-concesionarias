# R01 — Auditoría exhaustiva del proyecto original (informe de fase)

**Fase:** R01 · **Estado:** COMPLETADA · **Iniciativa:** VINOVA_PRO_FUNCTIONAL_REDESIGN

## 1. Referencia original investigada

`web_carros/` (Flask 3.1.3 + SQLite crudo + WeasyPrint + Cloudinary + MapTiler + SMTP simulado): 68 reglas de ruta → 66 endpoints, 15 tablas con DDL + 4 legacy, ~370 KB de Python (`vinova/core.py`, `vinova/routes/*.py`), 10 templates, 8 JS, 11 CSS.

## 2. Ámbitos auditados (8/8)

| Bloque | Entregable |
|---|---|
| Estructura/rutas/URLs | `reference-inventory.md` §1–2 (mapa completo de rutas) |
| Modelos/relaciones | §3–4 + `data-model-map.md` |
| Auth/roles/permisos | §5 |
| Clientes/cédula-RUC/vehículos | §6 |
| Postventa/mantenimientos | §7 |
| Facturas/manuales/PDF | §8 |
| Notificaciones/mapas/storage | §9–10 + `integrations-register.md` |
| Templates/JS/filtros/validaciones | §11–12 |
| Seguridad (conservar/no copiar) | §13 (S1–S22) |

## 3. Funcionalidades y hallazgos clave

- Cero usos de `Decimal` en la referencia; numeración de factura no única; impuesto manual sin motor de IVA.
- Entidad única `mantenimientos` (sin órdenes de taller ni citas); reglas km/meses derivadas.
- Códigos de canje aleatorios `VNV-XXXX-XXXX-XXXX` con transacción y snapshot de reversa; sin VIN.
- Garaje (`usuarios_vehiculos`) y vinculación con códigos: **brecha total** frente a VINOVA PRO.
- Cloudinary solo para avatares; MapTiler expuesto en cliente con fallback; manuales como estáticos públicos sin autorización.
- Guard central por prefijo de rol con comparación constante-tiempo; rate limit de login en memoria.

## 4. Paridad funcional (matriz)

`functional-parity-matrix.md` poblada con 55 filas: 25 IMPLEMENTADO (existencia verificada en VINOVA PRO con evidencia de archivo), 27 PENDIENTE (brechas reales), 1 DESCARTADO_CON_MOTIVO, 0 VALIDADO (validación por pruebas corresponde a R03–R15).

## 5. Diferencias justificadas (no copiar la referencia)

Lista S1–S22 en `reference-inventory.md` §13: scoping por sucursal ausente, montos float, sin CSP/HSTS, open redirect en enlaces de factura, manuales públicos sin verificación, colisión de numeración, etc. Cada decisión de no copia registrada en `decisions.md` (n° 7–15).

## 6. Modelos/migraciones

Ninguna en R01 (fase de solo lectura). `data-model-map.md` define equivalencias y entidades faltantes para R02.

## 7. Seguridad y permisos

Auditoría del guard de rol, CSRF, validadores, aislamiento de datos y rate limit; hallazgos S1–S22 con referencia exacta; sin modificación de código.

## 8. Pruebas ejecutadas

- `python manage.py check` → **OK, sin errores** (ejecutado al cerrar la fase).
- No corresponde suite completa (sin cambios de código).

## 9. Fallos pendientes

Los 5 preexistentes de R00 siguen documentados (`tmp/r00/pytest_full2.log`); no bloquean.

## 10. Commit local

Commit `R01: exhaustive reference audit - inventory, parity matrix, model map, integrations` (documentación únicamente; `web_carros/` excluida).

## 11. Próxima fase y punto de reanudación

- **Siguiente:** R02 — Arquitectura y brechas funcionales (comparar cada fila de la matriz con VINOVA PRO, definir entidades/modelos/permisos/sucursales/migraciones/pruebas).
- **Reanudar en:** `docs/vinova-redesign/functional-parity-matrix.md` → convertir filas PENDIENTE en diseño de R02; `data-model-map.md` → entidades nuevas.
