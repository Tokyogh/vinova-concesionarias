# F16 — Informe final de seguridad y consolidación

Fecha de cierre local: 2026-10-17
Rama: `integration/lite-pro`
Base de la misión: `9f04aaf`
Candidato certificado antes del commit F16: `f8888aa7` más las correcciones descritas aquí

## Veredicto

VINOVA PRO queda **apto para beta controlada en un entorno candidato** según la evidencia local y aislada de F0–F16. No se declara `PRODUCTION READY`, seguridad absoluta ni cumplimiento legal definitivo. Continúan pendientes los gates que requieren infraestructura, proveedores, revisión profesional y ejecución humana.

No se desplegó, no se hizo merge, no se modificó `web_carros/` y no se utilizaron datos personales reales.

## Resultado de la misión F0–F16

| Área | Resultado demostrado |
|---|---|
| inventario y paridad | continuidad desde B12; se cerraron sedes enriquecidas y catálogo público de repuestos sin reintroducir SRI, SaaS ni históricos |
| amenazas y ASVS | modelo CIA/STRIDE con 25 riesgos; 253 requisitos ASVS 5.0 L1/L2 inventariados con estado conservador y evidencia trazable |
| entradas y archivos | validación contextual de nombres, identificadores, teléfonos, placas, coordenadas, URLs, importaciones y archivos; límites ZIP/XLSX/archives y traversal verificados |
| autenticación y sesiones | cookies productivas `__Host-`, rotación y revocación de sesiones, política de contraseñas/2FA y controles de cuenta activa |
| acceso Staff | política configurable de red, dispositivo y riesgo; aprobación temporal con 2FA, rango superior, no autoaprobación y recuperación; apagada por defecto |
| privacidad y consentimiento | categorías firmadas, rechazo equivalente, bloqueo previo de preferencias/analítica/mapas y retirada; borradores legales pendientes de revisión profesional |
| supply chain y continuidad | lock con hashes, imágenes por digest, SBOM, límites de recuperación y paquete verificable; restore real y AV/CDR siguen externos |
| documentación | documentación canónica y comentarios ES→EN en fuentes elegibles; 30 documentos beta y 233 casos manuales pendientes de ejecución humana |

La matriz ASVS conserva 133 requisitos `Parcial`, 49 `Verificado localmente`, 59 `No aplica justificado` y 12 `Pendiente de proveedor o infraestructura`. Estos estados no equivalen a una certificación.

## Defectos detectados durante F16

### Contrato productivo de la cookie de consentimiento

El chequeo `vinova_security.E015` exigía correctamente el prefijo `__Host-`, pero la regresión de settings productivos no incluía la nueva variable. Se actualizó el baseline seguro y el caso negativo para demostrar `E013`, `E014` y `E015`. No se debilitó el control.

### Comentarios CSS multilínea dañados

La automatización F13 había reemplazado únicamente la primera línea de 39 encabezados CSS heredados. Los cierres `*/` quedaron huérfanos y el navegador descartaba la primera regla de cada hoja. El impacto incluía:

- portada del login superpuesta sobre el formulario;
- reglas base de `box-sizing`, layouts y responsive no aplicadas;
- desbordamiento móvil de instituciones;
- fallos visuales en páginas públicas e internas.

Se restauró la apertura de cada comentario sin cambiar reglas visuales. El auditor bilingüe ahora:

- conserva encabezados VINOVA multilínea al anteponer la cabecera ES/EN;
- falla en modo estricto si cualquier CSS tiene delimitadores desbalanceados.

Las 53 hojas CSS quedaron balanceadas y la matriz visual pública/login volvió a aprobar.

### Precondiciones E2E

- Los escenarios que prueban tema, favoritos y vistas guardadas ahora declaran consentimiento de preferencias mediante una cookie firmada. Analítica y contenido externo permanecen apagados.
- Dos casos usaban dígitos dentro de nombres (`E2E`), que la validación de dominio rechazó correctamente. Los datos sintéticos se cambiaron a `Pruebas`; no se relajó la validación.

## Evidencia final ejecutada

| Gate | Resultado |
|---|---|
| Django `check` y drift de migraciones | 0 incidencias; 0 migraciones sin generar |
| Ruff y `compileall` | aprobados |
| sintaxis JavaScript | 7 archivos propios aprobados |
| suite Python completa | **2.602 aprobadas, 41 omitidas, 0 fallos** |
| seguridad/RBAC/inputs/cookies/Staff focal | **2.020 aprobadas, 1 omisión intencional** |
| cookies y deployment focal | **13 aprobadas** |
| concurrencia PostgreSQL real | **7 aprobadas**; la primera invocación SQLite se descartó y no se usó como evidencia |
| E2E público + autenticación tras corrección | **15 aprobadas** |
| E2E clientes + ventas tras datos válidos | **2 aprobadas** |
| E2E Chromium final | **33 aprobadas, 0 fallos, 0 omisiones** en 11 dominios/escenarios |
| migraciones PostgreSQL aisladas | todas aplicadas; 0 pendientes |
| release readiness con DB y Celery | **11/11**; broker, worker y 6 tareas críticas verificados |
| producción aislada | `check --deploy`: 0 incidencias con valores QA fuertes y explícitos |
| dependencias instaladas | `pip check`: sin roturas |
| dependencias de producción | `pip-audit -r requirements/production.lock`: 0 vulnerabilidades conocidas |
| paquete de entrega temporal | 1.412 entradas; ZIP y SHA-256 verificados |
| documentación bilingüe | 576 Python, 211 HTML, 53 CSS, 7 JS y 61 archivos operativos; 0 brechas |
| guías beta | 30 archivos, 25 guías de rol/módulo, 233 casos únicos, 0 desviaciones |

Los 41 skips de la suite general corresponden a 33 E2E y 7 casos PostgreSQL ejecutados y aprobados por separado, más una parametrización negativa intencional. No se modificaron pruebas para ocultar defectos.

El gate Trivy/Nginx estricto quedó demostrado en F11 sobre las imágenes y digests fijados. F16 repitió el lock Python, el paquete, la configuración estática y el runtime QA; no se atribuye a F16 una nueva aprobación de infraestructura externa.

## Seguridad, privacidad y validación

- Se conservaron RBAC, ownership, alcance por sucursal, feature flags y mínimo privilegio.
- Los controles Staff se probaron apagados, monitorizados, denegados y aprobados temporalmente; no se activó una política que pueda bloquear administradores reales.
- Preferencias opcionales no persisten sin consentimiento; la suite E2E declara esa precondición cuando corresponde.
- Los formularios continuaron rechazando caracteres incompatibles en nombres; las pruebas se adaptaron con datos válidos.
- Los borradores legales identifican campos empresariales y decisiones pendientes; requieren revisión jurídica ecuatoriana antes de publicación definitiva.

## Gates externos pendientes

- staging candidato con DNS, TLS, proxy y cabeceras reales;
- ciclos reales de correo, Sentry, Cloudinary/S3, MapTiler y webhooks;
- restricciones de dominio para claves públicas y verificación de proveedores;
- restore real, rollback y capacidad sobre infraestructura candidata;
- antivirus/CDR para uploads externos;
- decisión empresarial de activar 2FA y política Staff, con recuperación ensayada;
- revisión jurídica de privacidad, conservación, contratos y transferencias;
- aprobación visual humana LITE→PRO y ejecución de los 233 casos beta.

Ningún gate externo se marcó aprobado sin ejecutarlo.

## Estado Git y entrega

La serie F0–F15 está separada en commits estables desde `94eb906` hasta `f8888aa7`. El commit F16 incorpora únicamente correcciones y evidencia de cierre. Los cambios locales ajenos de `AGENTS.md` y `.gitignore` permanecen sin preparar. Antes del push se verifica índice, ausencia de cambios en `web_carros/`, divergencia del remoto y `diff --check`.
