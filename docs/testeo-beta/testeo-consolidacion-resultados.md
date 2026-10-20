# Testeo beta — consolidación de resultados

## Procedimiento

1. Congele una versión/commit y registre los módulos habilitados.
2. Entregue copias en blanco de la plantilla y sólo las guías aplicables al rol.
3. Reciba los registros humanos en un repositorio privado de evidencia; no los mezcle con estas guías maestras.
4. Valide que cada estado tenga resultado obtenido y que `fallido` enlace una incidencia.
5. Deduzca duplicados por caso, causa, versión y recurso; conserve todos los evaluadores afectados.
6. Reproduzca incidencias críticas/altas en un entorno aislado antes de corregir.
7. Tras una corrección, ejecute el caso original, pruebas negativas de permisos y acceso a datos ajenos y regresiones automatizadas relacionadas.
8. Publique el resumen sin datos personales y mantenga los gates externos separados.

## Tabla de consolidación

| ID caso | Rol | Ejecuciones | Aprobadas | Fallidas | Bloqueadas | No aplica | Incidencias | Última versión | Decisión |
|---|---|---:|---:|---:|---:|---:|---|---|---|
| | | | | | | | | | |

## Criterios de salida

- Ningún caso crítico de autenticación, autorización, aislamiento de datos, integridad o privacidad puede quedar fallido.
- Un caso bloqueado no cuenta como aprobado y debe indicar responsable/gate externo.
- Los skips automatizados y casos `no aplica` requieren justificación trazable.
- “Pruebas verdes” no equivale a producción lista si faltan staging, TLS, proveedores, restauración ensayada, revisión legal o aprobación humana.

## Informe de ronda

- Commit evaluado:
- Cobertura por rol:
- Cobertura por módulo:
- Incidencias por severidad:
- Riesgos residuales:
- Gates externos:
- Recomendación: `continuar` / `continuar con reservas` / `detener`.
- Aprobador y fecha: custodiar por separado si incluye firma.
