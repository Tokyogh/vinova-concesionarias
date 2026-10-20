# F5 — validación y sanitización contextual

Fecha: 2026-10-15

## Alcance verificado

Se revisaron las superficies de entrada reutilizando la evidencia funcional B0–B12 y concentrando cambios en brechas reproducibles. La regla aplicada es validar el tipo y el contexto en backend, conservar el significado del dato y dejar el escape de salida a Django; no se introdujo un filtro universal destructivo.

| Entrada | Control verificado o añadido | Evidencia principal |
|---|---|---|
| nombres | letras y marcas Unicode, espacios, apóstrofes, punto y guion; rechazo de dígitos y controles invisibles | `validate_human_name`; formularios y serializers de cuentas, clientes y leads |
| teléfonos | presentación local/internacional con 7–15 dígitos y separadores acotados | `validate_phone_number`; HTML y REST |
| cédula/RUC | formato y dígito verificador ecuatoriano existente, ahora también aplicado a importaciones | `apps/customers/identification.py`; parser CSV/XLSX |
| correo | `EmailField`/DRF y validador Django en importaciones | formularios, serializers y `apps/imports/parsing.py` |
| placas | expresión regular configurable por `VINOVA_VEHICLE_PLATE_PATTERN` | vehículo HTML, búsqueda, REST e importaciones |
| VIN/chasis | 6–40 letras, números o guiones, normalizados a mayúsculas al persistir | vehículo HTML, REST e importaciones |
| año/kilometraje | 1886 a año actual + 2; enteros reales y no negativos | validadores, campos positivos y parser |
| dinero/stock | `Decimal` finito, precisión del modelo y valor no negativo según dominio | vehículos, inventario, leads e importaciones |
| coordenadas | `Decimal` y rangos latitud `[-90, 90]`, longitud `[-180, 180]` | modelo/formulario/serializer de sucursales y regresiones B12 |
| URLs | `URLField`; sitio público limitado a HTTP/HTTPS; enlaces externos con `noopener noreferrer` | sede y directorio público |
| búsquedas | ORM parametrizado, consultas normalizadas/acotadas y resultados limitados | `apps/common/search.py`, lookups y formularios de filtro |
| archivos | extensión, límite de bytes y firma/contenedor real para imágenes, PDF, Office, CSV, PKCS#12, video y modelos 3D | `apps/common/validators.py` y regresiones de upload |
| CSV/XLSX | storage privado, tipo real, parsers acotados por dominio y validación por fila antes de confirmar | `apps/imports/`; `full_clean()` antes de persistir |
| contraseñas | se conserva el valor exacto; solo actúan validadores de contraseña | formularios de registro/cambio y regresión nueva |
| texto libre | longitud del campo, rechazo de controles invisibles peligrosos y escape contextual de plantillas | validadores de dominio y autoescape Django |

## Brechas corregidas

1. Formularios y serializers REST aplicaban reglas distintas para nombres, teléfonos, placas y montos.
2. La placa no disponía de política configurable por jurisdicción.
3. CSV/XLSX podía aceptar `NaN`, `Infinity`, enteros fraccionarios, placas/VIN malformados, contactos inválidos y montos negativos en algunos dominios.
4. La confirmación de importaciones persistía vehículos, clientes o artículos sin ejecutar `full_clean()`.
5. Caracteres Unicode legítimos y contraseñas necesitaban una regresión explícita que evitara sanitización destructiva.

## Decisiones de seguridad

- No se reescriben nombres, direcciones, textos libres ni contraseñas.
- Nueva línea, retorno y tabulación siguen permitidos en textos multilínea; se bloquean controles Unicode invisibles incompatibles.
- Las URLs meramente mostradas no se someten a resolución DNS. Los destinos de conexiones salientes requieren defensas SSRF adicionales y se tratan en F6.
- No se declara análisis antivirus/CDR: F12 confirmó que esa capacidad necesita motor o proveedor y permanece como brecha explícita.
- F12 añadió límites de filas, columnas, miembros ZIP, bytes descomprimidos y ratio de compresión. El sandbox de procesamiento y la validación con carga real permanecen pendientes de infraestructura.

## Pruebas

- `apps/common/tests/test_domain_input_validation.py`: 21 casos positivos, negativos y de límite.
- `apps/imports/tests/test_mass_imports.py`: 17 casos, incluidos cuatro de entrada adversarial añadidos.
- Regresión de dominios afectados: 202 pasaron y 4 fueron omitidas por condiciones declaradas.
- `python manage.py check`: sin problemas.
- `python manage.py makemigrations --check --dry-run`: sin cambios; el host local fuera de Docker no resolvió `db` al consultar el historial, sin afectar la detección de drift.
- Ruff focal: sin errores después de retirar imports no usados.

## Riesgo residual

La validación reduce datos malformados y bypasses entre canales, pero no sustituye autorización, encoding de salida, hardening SSRF, límites de infraestructura ni inspección antimalware. Esos controles continúan en F6 y F12.
