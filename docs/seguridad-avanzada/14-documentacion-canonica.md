# F14 — README y documentación canónica

Fecha de evidencia local: 2026-10-16

## Resultado

La documentación vigente quedó alineada con los cambios demostrados en F1–F13 sin reescribir históricos B0–B12 ni duplicar los documentos especializados. Los cierres anteriores conservan su fecha y alcance; `docs/seguridad-avanzada/ESTADO_ACTIVO.md` es el checkpoint actual.

## Superficies actualizadas

| Tema | Documento canónico | Cambio principal |
|---|---|---|
| visión, estado y despliegue | `README.md` | capacidades, controles, lock/SBOM y gates actuales |
| índice | `docs/README.md` | acceso directo a evidencia F3–F13 |
| arquitectura | `docs/ARQUITECTURA.md` | repuestos sin modelo paralelo, acceso Staff, consentimiento y límites de archivos |
| funcionalidades | `docs/FUNCIONALIDADES.md` | sedes/repuestos cerrados y privacidad/seguridad actuales |
| autorización | `docs/ROLES_PERMISOS.md` | RBAC independiente de la aprobación Staff temporal |
| seguridad y ASVS | `docs/SECURITY.md` | riesgos cerrados, estados conservadores y pendientes reales |
| configuración | `docs/CONFIGURACION.md` | catálogo, cookie firmada y política Staff auditada en base |
| integraciones | `docs/API.md` | protección SSRF/DNS y composición de scopes/permisos/acceso Staff |
| despliegue/operación | `docs/PRODUCCION.md`, `docs/OPERACION.md` | supply chain, AV/CDR, consentimiento, recuperación y revisión periódica |
| calidad | `docs/TESTING.md` | auditoría bilingüe y perfiles reales PostgreSQL/Chromium |
| estado/paridad | `docs/ESTADO_ACTUAL.md`, `docs/PARIDAD_LITE_PRO.md` | brechas cerradas retiradas; gates externos conservados |
| historial de producto | `docs/CHANGELOG.md` | consolidación post-2.0 sin resultados efímeros |

## Criterios de precisión

- No se actualizó `docs/auditoria-integral/12-informe-final.md`: es evidencia histórica fechada, no el estado actual.
- Los borradores legales permanecen pendientes de identidad empresarial, plazos y aprobación profesional.
- No se declara `PRODUCTION READY`, seguridad absoluta ni cumplimiento ASVS/LOPDP global.
- Antivirus/CDR, restore medido, staging/TLS/proveedores, firma del artefacto y beta humana siguen abiertos.
- Los mecanismos detallados se explican una sola vez en `docs/seguridad-avanzada/`; los documentos canónicos resumen y enlazan.

## Verificación

- búsqueda dirigida de afirmaciones obsoletas sobre sedes, repuestos, lock, DNS y CSP: sin coincidencias en documentos canónicos;
- 149 archivos Markdown recorridos, con cero enlaces locales rotos;
- `git diff --check` y auditoría bilingüe estricta: aprobados;
- ningún cambio en `web_carros/` ni en comportamiento de aplicación.
