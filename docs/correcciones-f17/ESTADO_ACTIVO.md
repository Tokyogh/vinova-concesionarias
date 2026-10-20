# F17 — Estado activo

Fecha: 2026-10-19
Rama: `integration/lite-pro`
Base: `fd51251b`

## Bloque actual

F17.12 — cierre local completado; permanecen únicamente gates externos y ejecución beta humana.

## Avances

- Rama, HEAD y remoto verificados: local y `origin/integration/lite-pro` sincronizados al iniciar.
- Cambios ajenos identificados y excluidos: `AGENTS.md` y `.gitignore`.
- Flujos relevantes localizados sin modificar `web_carros/`.
- F17.1–F17.4: defectos de contacto reproducidos, validadores reutilizados y obligatoriedad contextual definida.
- Solicitudes comerciales conservadas como captura pública referencial, con Decimal, límites técnicos y rate limiting existente.
- Auditor heredado de contacto añadido como procedimiento de solo lectura y sin exposición del valor.
- F17.5: UI y backend alineados al emisor real `VNV-XXXX-XXXX-XXXX-XXXX`.
- F17.6: canje sin kilometraje del cliente; kilometraje técnico desconocido representado como `NULL`.
- F17.7: gestión de multimedia, destacados y especificaciones; identidad técnica protegida con motivo, auditoría y estados comerciales.
- F17.8: gestión de artículos bajo `help.manage`, con vista previa, publicación, historial, restauración, escape y auditoría.
- F17.9: drawers público/portal corregidos, topbar Staff contenida y navegación responsive verificada en Chromium.
- F17.10: 15 mapas funcionales generados desde rutas reales con Chromium, datos sintéticos, leyendas numeradas y trazabilidad de modelos, campos, selectores, servicios, permisos y estados vacíos.
- La evidencia cartográfica ejercitó la sede sintética de Quito y el proveedor configurado sin publicar su clave.
- El recorrido visual detectó y corrigió dos tablas de administración vehicular que no usaban el contenedor responsive existente.
- F17.11: README e índices técnicos enlazan los mapas; la guía beta F17 define 15 casos manuales con metadatos y todos permanecen `pendiente`.
- F17.12: runner Windows reparado, host PostgreSQL QA acotado, suite/regresiones completas aprobadas e informe final emitido.

## Pendientes

- Ejecutar en infraestructura candidata los gates externos enumerados en `INFORME_FINAL.md`.
- Ejecutar y documentar humanamente los 248 casos beta; 15 corresponden a F17.

## Bloqueos

- No existe una política empresarial aprobada de montos mínimos comerciales; no se inventó una.

## Pruebas

- F17 contacto/solicitudes: 10 aprobadas.
- Regresión de cuentas, clientes, leads, privacidad y portal: 201 aprobadas, 5 omitidas.
- F17 vehículos focal: 58 aprobadas, 1 omitida; vehículos+portal: 113 aprobadas, 3 omitidas.
- Centro de ayuda: 16 aprobadas.
- Responsive público/accesibilidad: 19 escenarios completados; portal focal: 1 aprobada.
- Django check, Ruff y compileall: aprobados.
- JavaScript: 7 archivos con sintaxis válida; migraciones sin drift.
- Mapas funcionales: escenario aislado Docker/Chromium, 1 aprobado, 0 fallos; 15 capturas verificadas.
- Documentación: enlaces locales íntegros, 15 casos F17 pendientes y auditoría bilingüe estricta sin faltantes.
- QA full PostgreSQL: 9/9 gates; 2.669 pruebas aprobadas, 35 omitidas y 0 fallos.
- Seguridad/RBAC/ownership focal: 2.079 aprobadas y 1 omisión intencional.
- Concurrencia PostgreSQL: 6 aprobadas; migraciones completas aplicadas en base efímera.
- E2E Chromium: 34 aprobadas en 12 escenarios, sin fallos ni omisiones.

## Commits

- `ac5ff352`: validación de contacto y solicitudes comerciales.
- `7ad5c474`: canje y administración ampliada de vehículos.
- `d6c604a2`: gestión versionada de ayuda contextual.
- `151eb2e4`: navegación responsive pública, portal y Staff.
- `0df9e2f2`: mapas funcionales trazados y regresión visual.
- `150ab95b`: guía beta F17 e índices técnicos.
- `1c1bad39`: guía F17 alineada con su auditor.
- `23fbed0f`: wrappers Windows y salvaguarda QA corregidos.
- Commit de cierre: informe final y checkpoint (este bloque).

## Próxima acción exacta

No queda una acción local ejecutable dentro de F17; conservar los gates externos como pendientes reales.
