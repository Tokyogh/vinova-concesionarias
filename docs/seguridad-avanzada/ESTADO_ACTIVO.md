# Seguridad avanzada — estado activo

Fecha: 2026-10-17
Rama: `integration/lite-pro`
Base de continuidad: `9f04aaf`

## Fase actual

F16 completada localmente. El candidato queda apto para beta controlada, no `PRODUCTION READY`.

## Último bloque completado

- Se certificaron checks, migraciones, PostgreSQL, Celery, suite Python, E2E Chromium, dependencias, paquete y documentación.
- Se corrigió la regresión de 39 comentarios CSS multilínea introducida por la normalización documental y se añadió un gate de balance.
- Las pruebas de preferencias declaran consentimiento firmado sin habilitar analítica ni medios externos.
- Los datos E2E de nombres respetan la validación del dominio; no se relajaron controles.

## Evidencia

- `docs/seguridad-avanzada/16-informe-final.md`.
- suite Python: 2.602 aprobadas, 41 omitidas y 0 fallos;
- focal seguridad/RBAC/inputs/cookies/Staff: 2.020 aprobadas y 1 omisión intencional;
- PostgreSQL/concurrencia: 7 aprobadas;
- E2E Chromium: 33 aprobadas, 0 fallos y 0 omisiones;
- release readiness: 11/11 con DB, broker, worker y tareas críticas;
- `pip-audit` sobre `requirements/production.lock`: 0 vulnerabilidades conocidas;
- auditoría bilingüe: 0 brechas y 0 CSS desbalanceados;
- guías beta: 30 archivos y 233 casos únicos.

## Bloqueos externos

- staging con DNS/TLS/proxy reales y ciclos de proveedores;
- restore/rollback sobre infraestructura candidata y gate antivirus/CDR;
- activación empresarial de 2FA/acceso Staff con recuperación ensayada;
- revisión jurídica y datos legales definitivos;
- aprobación visual humana y ejecución de los 233 casos beta.

## Commits

- `9f04aaf`: cierre integral B12, punto de partida.
- `94eb906`: checkpoint F0.
- `c3de717`: auditoría incremental F1.
- `54a3942`: cierre de brechas funcionales F2.
- `d5b3c68`: modelo de amenazas F3.
- `d5c21db`: matriz ASVS F4.
- `4c724bd`: validación contextual F5.
- `b9cb7bf`: hardening de aplicación F6.
- `ee71582`: cookies y sesiones F7.
- `223f090`: acceso Staff adaptativo F8.
- `b978c20`: consentimiento granular F9.
- `7eb68ae`: privacidad y borradores legales F10.
- `43a9aeb`: lock, SBOM y cadena de suministro F11.
- `57ff7a1`: disponibilidad, archivos y restore F12.
- `5c25843`: cabeceras y docstrings F13a.
- `9339b61c`: operación y secciones internas F13b.
- `3f5f1485`: documentación canónica F14.
- `f8888aa7`: guías beta F15.
- F16: este commit de certificación final y regresiones; el hash se consulta en `git log`.

## Próxima acción exacta

Ejecutar los gates externos en staging candidato, obtener revisión jurídica y realizar la beta humana documentada antes de cualquier decisión de producción.

## Historial compacto

- F0–F2: continuidad, auditoría incremental y brechas funcionales cerradas.
- F3–F4: modelo CIA/STRIDE y matriz completa ASVS 5.0 L1/L2.
- F5–F9: validación, hardening, sesiones, acceso Staff y consentimiento granular.
- F10–F12: privacidad/legal, supply chain y continuidad/archivos.
- F13–F15: documentación bilingüe, documentación canónica y guías beta.
- F16: certificación local integral, corrección de regresión CSS y cierre verificable.
