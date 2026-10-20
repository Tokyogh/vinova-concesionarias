# F17 — Informe final de corrección funcional e integridad

Fecha de cierre local: 2026-10-19

Rama: `integration/lite-pro`

Base F17: `fd51251b`

Candidato validado antes del informe: `23fbed0f`

## Veredicto

Las correcciones ejecutables de F17 quedan **aptas para beta controlada** sobre el candidato validado. No se declara `PRODUCTION READY`, seguridad absoluta ni cumplimiento legal definitivo. No se desplegó, no se hizo merge, no se alteró producción y `web_carros/` permaneció intacto.

Los 15 casos manuales específicos de F17 continúan `pendiente`; la evidencia automatizada no sustituye su ejecución humana ni los gates externos.

## Defectos reportados, causas y correcciones

| Área | Confirmación y causa raíz | Corrección demostrada |
|---|---|---|
| teléfono y WhatsApp | perfil cliente y privacidad aceptaban texto porque no reutilizaban el validador común | validación compartida en backend, ayudas frontend e inputs telefónicos; auditor heredado de solo lectura |
| obligatoriedad | se podía elegir un canal sin aportar su dato | teléfono, WhatsApp o correo se vuelven obligatorios solo cuando son el canal elegido; presencial no inventa requisitos |
| solicitudes comerciales | Django ya rechazaba `5 usd`, pero faltaba un máximo explícito | Decimal con dos decimales y máximo técnico `9.999.999.999,99`; sigue siendo interés público referencial, no transacción |
| código VNV | textos y máscaras heredados mostraban tres grupos, mientras el emisor PRO genera cuatro | frontend y backend alineados con `VNV-XXXX-XXXX-XXXX-XXXX`, sin cambiar códigos ya emitidos |
| canje de vehículo | la interfaz pedía kilometraje al cliente | canje solo por código; kilometraje administrado o `NULL` como “No registrado”, nunca cero inventado |
| administración vehicular | relaciones existentes no tenían interfaz completa | CRUD autorizado de multimedia, destacados y especificaciones; identidad técnica exige razón y estado permitido; auditoría y alcance por sede |
| ayuda | el contenido dependía de código/despliegue | creación, edición, preview, publicación, despublicación, historial y restauración bajo `help.manage`, transacciones y versiones inmutables |
| navegación | público colisionaba en tablet, portal carecía de drawer completo y topbar Staff podía crecer | breakpoints coherentes, drawers con foco/Escape/overlay, truncado Staff y regresión de teclado/overflow |
| mapas funcionales | no existía una fuente visual trazable | 15 capturas reales, anotadas, con datos sintéticos y documentación de modelos, campos, selectores, servicios, permisos y estados vacíos |
| ficha vehicular | la captura detectó dos tablas con una clase responsive inexistente | reutilización de `responsive-table`; sin overflow de documento en Chromium |
| runner Windows | un BOM incrustado antes de `param` hacía que `qa-full.cmd` ejecutara `quick`; encabezados CMD no ASCII producían comandos espurios | BOM eliminado, preámbulos CMD compatibles y prueba binaria de regresión; el wrapper ejecutó después `full` correctamente |
| preparación QA en Docker | la salvaguarda local no reconocía el hostname efímero `qa_db` | se añadió únicamente `qa_db`; producción y hosts remotos siguen denegados y tienen prueba negativa |
| contrato E2E | una prueba seguía fijada en 11 archivos | expectativa actualizada a 12 y presencia explícita del escenario de mapas |

## Funciones y controles modificados

- Formularios y validadores de registro, perfil, privacidad, clientes, leads y solicitudes conservan validación contextual y mensajes seguros.
- El servicio de canje sigue siendo transaccional, consume códigos una vez y no permite acceso horizontal.
- Los servicios vehiculares verifican `vehicles.manage`, `vehicles.publish` o `vehicles.link_codes`, alcance de sucursal, relaciones y transiciones antes de escribir.
- La ayuda visible continúa filtrada por publicación, categoría, rol y permiso; `is_staff` no reemplaza `help.manage`.
- Los shells público, portal y Staff mantienen alternativas de navegación accesibles en todos los breakpoints probados.
- Los comandos QA permanecen limitados a entornos y hosts explícitos; el cambio no autoriza una base remota.

## Seguridad y ASVS

F17 conservó los controles de autenticación, sesiones, cookies, CSRF, RBAC, ownership, alcance por sucursal, módulos ON/OFF, uploads y auditoría certificados localmente en F16. Las regresiones focales ejercitaron validación de entradas, control de acceso, exposición de información, escalada, documentos, cookies y acceso Staff adaptativo.

La evidencia refuerza las áreas ASVS 5.0 relativas a validación/encoding, archivos, autenticación/sesiones, autorización, logging, protección de datos y configuración. No cambia por sí sola los estados conservadores de la [matriz ASVS](../seguridad-avanzada/04-matriz-asvs.md) ni equivale a certificación externa.

## Evidencia visual y documental

- Índice y trazabilidad: [`docs/mapas-funcionales/`](../mapas-funcionales/README.md).
- 15 PNG controlados sobre rutas reales; Chromium verificó respuesta 200, componentes y ausencia de overflow.
- Instituciones ejercitó una sede sintética de Quito y el mapa configurado sin exponer la clave del proveedor.
- Guía manual: [`testeo-correcciones-f17.md`](../testeo-beta/testeo-correcciones-f17.md), 15 casos `FCR-001..FCR-015`, todos `pendiente`.
- Auditor de guías: 31 archivos, 25 guías de rol/módulo, 248 casos únicos y 0 desviaciones.
- Auditor bilingüe: 582 módulos Python, 216 HTML, 53 CSS, 7 JavaScript y 61 archivos operativos; 0 faltantes y 0 comentarios CSS desbalanceados.

## Validación final

| Gate | Resultado |
|---|---|
| Django check y drift | aprobados, 0 incidencias y 0 migraciones sin generar |
| Ruff y compileall | aprobados |
| JavaScript | 7 archivos con sintaxis válida |
| CSS / documentación bilingüe | 53 CSS balanceados; auditor estricto sin faltantes |
| perfil QA `full` aislado | 9/9 gates, 0 advertencias del runner, 0 fallos |
| suite Python completa en PostgreSQL | 2.669 aprobadas, 35 omitidas, 0 fallos |
| warnings Pytest | 2, producidos por la prueba negativa que apunta deliberadamente a `database.example.invalid` y su teardown; no ocultaron fallos |
| skips clasificados | 34 E2E ejecutados aparte y 1 parametrización negativa intencional |
| seguridad/RBAC/ownership focal | 2.079 aprobadas, 1 omisión intencional |
| PostgreSQL y migraciones | todas las migraciones aplicadas en base efímera; base destruida al finalizar |
| concurrencia PostgreSQL focal | 6 aprobadas: leads, numeración, ownership vehicular, notificaciones y PDF de factura |
| E2E Chromium | 34 aprobadas, 0 fallos, 0 omisiones en 12 archivos/escenarios |
| mapas focales | 1 escenario aprobado en ejecución dedicada; 15 capturas verificadas |
| OpenAPI y dependencias instaladas | aprobados por el perfil `full` |
| guías beta y enlaces Markdown | 248 casos íntegros; 0 enlaces locales rotos |
| diff y límites | limpio; 0 cambios en `web_carros/`; cambios ajenos de `.gitignore` y `AGENTS.md` preservados |

La primera invocación de `qa-full.cmd` reveló el BOM incrustado y solo ejecutó `quick`; no se contó como certificación. La primera corrida `full` real detectó cinco fallos: cuatro por el hostname `qa_db` no reconocido y uno por el conteo antiguo de escenarios. Tras corregir las causas y añadir regresiones, se repitió el perfil completo y terminó verde.

## Privacidad, cookies y acceso Staff

- No se usaron datos personales reales; los mapas crean registros sintéticos en la base temporal.
- No se imprimieron credenciales, claves MapTiler, tokens ni códigos VNV empresariales.
- La activación temporal de medios externos en E2E usa una cookie firmada solo en el contexto aislado.
- No se cambiaron políticas Staff ni se activó `enforce`; la matriz focal conserva red, 2FA, aprobación temporal, no autoaprobación y expiración.
- Los borradores legales y decisiones de conservación no se publicaron ni se declararon aprobados.

## Riesgos y gates restantes

- no existe una política empresarial aprobada de monto mínimo para solicitudes comerciales;
- staging con DNS/TLS, cabeceras y restricciones de dominio de la clave MapTiler;
- ciclos reales de correo, Sentry, Cloudinary/S3 y webhooks;
- restore, rollback y capacidad sobre infraestructura candidata;
- antivirus/CDR para archivos externos;
- revisión jurídica ecuatoriana de privacidad, conservación, contratos y transferencias;
- revisión visual humana y ejecución de los 248 casos beta, incluidos los 15 de F17;
- Firefox/WebKit y el perfil `release` completo no formaban parte del gate F17 solicitado; Chromium sí fue ejecutado íntegramente.

Ningún gate externo se marcó como aprobado.

## Commits F17

| Commit | Bloque |
|---|---|
| `ac5ff352` | validación de contacto y solicitudes comerciales |
| `7ad5c474` | canje y administración ampliada de vehículos |
| `d6c604a2` | gestión versionada de ayuda |
| `151eb2e4` | navegación responsive pública, portal y Staff |
| `0df9e2f2` | mapas funcionales trazados y regresión visual |
| `150ab95b` | guía beta F17 e índices técnicos |
| `1c1bad39` | alineación de la guía con su auditor |
| `23fbed0f` | robustez de los gates Windows y seguridad QA |

El commit que incorpora este informe y el checkpoint constituye el cierre documental. El push se limita a `origin/integration/lite-pro`, sin force push, merge ni despliegue.
