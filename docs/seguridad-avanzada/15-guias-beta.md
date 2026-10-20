# F15 — Guías beta sencillas y trazables

Fecha de evidencia local: 2026-10-16

## Resultado

Se actualizaron los 30 documentos `docs/testeo-beta/testeo-*.md`. Las 25 guías de rol o módulo reúnen 233 casos manuales únicos. Todos permanecen inicialmente en `pendiente`; la documentación no contiene resultados, firmas, credenciales ni datos personales reales.

## Cobertura añadida

| Rango | Cobertura | Casos nuevos |
|---|---|---:|
| `AS-011..AS-015` | política Staff apagada/monitoreada, bloqueo fuera de red, aprobación, revocación y recuperación | 5 |
| `ESP-011..ESP-012` | foto/website por sede y mapa sujeto a elección de privacidad | 2 |
| `INV-010..INV-012` | catálogo público, no exposición de datos internos y módulo OFF | 3 |
| `PA-014..PA-017` | aceptar/rechazar/configurar, bloqueo previo, retirada y textos legales | 4 |
| `RAI-014` | límites CSV/XLSX y enlaces externos | 1 |
| `IC-016..IC-018` | cambio DNS, límites de restore y gate antivirus/CDR | 3 |
| `QAC-011` | auditoría documental bilingüe | 1 |

## Facilidad de ejecución

- El índice explica “alcance”, acceso a datos ajenos y los términos técnicos inevitables.
- Cada caso indica dónde entrar o qué flujo abrir, qué acción realizar y qué debe observarse.
- La plantilla individual registra entorno, commit, rol, dispositivo, política Staff, elección de cookies, evidencia y observaciones.
- Los casos de riesgo exigen entorno desechable o responsable técnico; no piden pruebas destructivas ni malware real.
- Los datos de prueba deben ser sintéticos y la evidencia debe omitir cédulas completas, secretos, tokens, cookies y archivos privados.

## Auditoría reproducible

`scripts/audit_beta_guides.py` comprueba:

- presencia de objetivo, precondiciones, tabla de casos y checklist;
- columnas de pasos, resultado esperado/obtenido, estado, evidencia y observaciones;
- IDs únicos, pasos numerados, estado maestro `pendiente` y referencia en checklist;
- ausencia de jerga no explicada y posibles identificadores personales de diez dígitos.

Resultado antes del commit: 30 archivos, 25 guías de rol/módulo, 233 casos y cero desviaciones. La ejecución humana, aprobación visual y conformidad continúan pendientes.
