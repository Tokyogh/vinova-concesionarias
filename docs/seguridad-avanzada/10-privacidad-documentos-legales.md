# F10 — Privacidad y documentos legales

Fecha técnica: 2026-10-16
Estado: borrador pendiente de revisión profesional y aprobación empresarial

## Marco de referencia

La implementación toma como referencia inicial, sin declarar cumplimiento definitivo:

- [Ley Orgánica de Protección de Datos Personales](https://www.registroficial.gob.ec/267223-2/), publicada por el Registro Oficial;
- [Reglamento General de la LOPDP, Decreto Ejecutivo 904](https://www.registroficial.gob.ec/tercer-suplemento-al-registro-oficial-no-435/);
- [resoluciones vigentes de la Superintendencia de Protección de Datos Personales](https://spdp.gob.ec/resoluciones2/), incluidas reglas posteriores sobre contratos, transferencias, delegado y eliminación/anonimización.

La aplicabilidad, base jurídica, plazos, delegado, evaluaciones de impacto, transferencias y contenido contractual deben confirmarse con profesionales y con la operación real de la empresa.

## Documentos públicos preparados

| Documento | Ruta | Estado |
|---|---|---|
| política de privacidad | `/privacy/policy/` | borrador visible, versionado y configurable |
| política de cookies | `/privacy/cookie-policy/` | borrador alineado con el inventario F9 |
| términos y condiciones | `/privacy/terms/` | borrador; condiciones comerciales pendientes |
| aviso legal | `/privacy/legal-notice/` | borrador; representante y canal legal pendientes |
| preferencias de cookies | `/privacy/cookies/` | control operativo revocable |
| solicitud del titular | `/privacy/request/` | control operativo con verificación de identidad |

Todas las páginas muestran una advertencia de borrador y `PENDIENTE DE COMPLETAR` para datos no confirmados. Los datos de razón social, RUC, domicilio y contacto se muestran solo cuando ya están configurados en la empresa; no se inventan.

## Consentimiento y aceptación

- El registro de clientes separa la aceptación de términos de la constancia de lectura del aviso de privacidad.
- La lectura del aviso no se presenta como consentimiento para marketing, analítica o cookies.
- La auditoría del registro conserva los booleanos y versiones aplicadas, no el texto completo ni datos nuevos.
- El formulario de lead solicita una autorización específica para responder la solicitud comercial y enlaza el aviso.
- `ConsentRecord` conserva versión del aviso, fecha, finalidad, fuente y evidencia mínima existente.
- Las cookies opcionales mantienen su mecanismo independiente de F9.

## Capacidades ya implementadas

- Solicitudes públicas de acceso, exportación, corrección, eliminación/anonimización, oposición y revocación.
- Verificación de identidad previa a entrega o modificación.
- Exportaciones privadas, con hash y vencimiento.
- Retención legal explícita que bloquea anonimización.
- Anonimización transaccional y auditada, sin borrar automáticamente registros sujetos a revisión.
- Revocación de consentimientos activos vinculados de forma controlada.
- RBAC y alcance por sucursal para gestión interna.

## Datos pendientes antes de producción

- Identidad legal definitiva, representante, domicilio y contacto exclusivo de privacidad.
- Determinación y datos del delegado de protección de datos, si resulta obligatorio.
- Inventario contractual de encargados, subencargados, ubicaciones y transferencias.
- Bases jurídicas aprobadas por finalidad y prueba de interés legítimo cuando corresponda.
- Plazos legales definitivos por documentos, contabilidad, personal, seguridad y respaldos.
- Condiciones vinculantes de precio, reserva, pago, entrega, garantía, devoluciones y reclamos.
- Canal y responsables formales de incidentes y solicitudes.
- Aprobación jurídica, empresarial y fecha efectiva de cada versión.

## Evidencia técnica

- 865 pruebas focales y 2.116 pruebas integradas aprobadas; 5 omisiones clasificadas.
- Django check, drift de migraciones y Ruff aprobados.
- No se requirió migración: las versiones viven en configuración y la evidencia usa la auditoría existente.

No se declara cumplimiento legal definitivo ni se autoriza publicar estos borradores como textos aprobados.
