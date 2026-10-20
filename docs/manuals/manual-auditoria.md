# Manual del auditor

Consulta de eventos, integridad, alertas y exportaciones de solo lectura.

- Tipo: `manual`
- Categoría: `seguridad`
- Permiso requerido: `audit.view`
- Roles específicos: `auditor, admin_general, superadmin`
- Ruta contextual: `audit_internal:list`

Manual del auditor

Objetivo
Revisar eventos de forma independiente sin alterar la operación examinada.

Procedimiento recomendado
1. Define periodo, usuario, sucursal, categoría y severidad.
2. Abre el detalle para revisar solicitud, objeto y cambios saneados.
3. Ejecuta la verificación de integridad cuando corresponda.
4. Gestiona alertas solo si tienes permiso específico.
5. Exporta la mínima información necesaria para el informe.

Controles importantes
• Una ausencia de eventos no demuestra por sí sola que una acción no ocurrió.
• Protege las exportaciones de auditoría.

Antes de terminar
□ Filtros documentados.
□ Hallazgos con evidencia.
□ Cadena de integridad verificada.
