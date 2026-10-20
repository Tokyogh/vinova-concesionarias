# B7 — Documentación regenerada

Fecha: 2026-10-15

## Fuentes canónicas

- `README.md`: presentación, capacidades, stack, arquitectura, estructura,
  instalación, configuración, roles, seguridad, testing y operación;
- `docs/README.md`: índice único y separación entre vigente e histórico;
- `docs/FUNCIONALIDADES.md`: inventario de producto y exclusiones;
- `docs/ARQUITECTURA.md`: capas, flujos y límites;
- `docs/BASE_DATOS.md`: motores, relaciones, integridad y migraciones;
- `docs/ROLES_PERMISOS.md`: semántica RBAC y enlace a matriz exhaustiva;
- `docs/SECURITY.md`: contrato de ingeniería y estado comprobado;
- `docs/API.md`: sesión/bearer, scopes, webhooks, BI y OpenAPI;
- `docs/PRODUCCION.md`: topología, despliegue y rollback;
- `docs/TESTING.md`: capas, comandos, perfiles y criterio de aceptación;
- `docs/OPERACION.md`: rutina e incidentes;
- `docs/PARIDAD_LITE_PRO.md`: resumen de equivalencia y brechas;
- `docs/ESTADO_ACTUAL.md`: capacidades, pendientes, gates y veredicto.

Los manuales y documentos especializados vigentes siguen enlazados. Los
informes antiguos no fueron borrados ni reescritos; el índice los identifica
como históricos necesarios para evitar que sus HEADs o cifras se confundan con
el corte actual.

## Exactitud

La documentación distingue implementado, probado localmente, pendiente,
excluido y gate externo. No presenta una dependencia instalada como control
activo sin evidencia, no incluye secretos y mantiene el veredicto **no
production ready**.

Validación ejecutada: 90 Markdown inspeccionados por el verificador de enlaces
locales, con **0 enlaces inexistentes**. La validación integral se repetirá en
B12 después de guías beta y limpieza.
