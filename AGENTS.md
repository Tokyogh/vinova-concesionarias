# AGENTS.md — VINOVA PRO

## Proyecto
- VINOVA PRO es la evolución empresarial de VINOVA LITE.
- PRO es monocompañía, no SaaS ni multi-tenant.
- `web_carros/` contiene LITE y es referencia funcional y visual de solo lectura.
- Conservar capacidades útiles de LITE y mejoras empresariales de PRO.
- PRO mantiene su arquitectura, modelos, servicios, permisos y seguridad.
- No duplicar modelos, servicios ni lógica innecesariamente.
- No reintroducir SRI, SaaS ni recordatorios automáticos de mantenimiento.

## Autonomía
- Trabajar autónomamente hasta completar el alcance solicitado.
- Dividir trabajos grandes en bloques verificables.
- No pedir confirmaciones intermedias salvo riesgos irreversibles, decisiones ambiguas o credenciales externas indispensables.
- Usar checkpoints MD compactos con estado, pendientes, bloqueos y próxima acción.
- Reanudar desde checkpoint y Git, sin repetir trabajo completado.
- Evitar lecturas extensas, análisis redundantes y salidas innecesarias.
- No inventar resultados, ocultar errores ni afirmar funciones no verificadas.

## Arquitectura
- Mantener separación entre modelos, servicios, selectores, vistas, formularios y APIs.
- Reutilizar componentes existentes antes de crear nuevos.
- Aplicar permisos y validaciones en backend.
- Respetar RBAC, ownership, sucursales, transacciones y auditoría.
- Los módulos deshabilitados no deben ser utilizables mediante URLs directas.
- Mantener HTML, CSS y JS organizados por componentes y secciones.
- No introducir refactorizaciones ajenas a la tarea.

## Paridad LITE → PRO
- El portal cliente debe replicar fielmente el diseño LITE: estructura, distribución, dimensiones, navegación, tarjetas, modales, tablas, gráficas e interacciones.
- Solo cambiar colores mediante tokens corporativos de PRO, salvo instrucción expresa.
- Mantener CSS/JS modular sin alterar la apariencia aprobada.
- Conservar comportamiento funcional usando modelos, servicios y seguridad de PRO.
- Comparar flujos completos: interfaz → permisos → servicio → persistencia → resultado.
- Registrar diferencias, omisiones, mejoras y excepciones justificadas.
- No copiar vulnerabilidades, SQL inseguro ni implementaciones obsoletas.
- Validar con pruebas unitarias, integración, E2E y comparación visual.
- No declarar paridad sin evidencia.

## Diseño
- Priorizar azules claros y celestes claros en el portal cliente.
- Reservar azules muy oscuros para contraste puntual.
- Conservar referencias visuales aprobadas sin reinterpretarlas.
- El logo superior izquierdo del portal cliente debe llevar al hub/index público principal.
- Mantener diseño responsive, accesible y profesional.

## Seguridad
- Validar y normalizar entradas según tipo y contexto.
- Usar ORM o SQL parametrizado.
- Aplicar escape contextual contra XSS y protección CSRF.
- Prevenir IDOR, SSRF, path traversal, mass assignment y accesos indebidos.
- Mantener rate limiting, autenticación segura, 2FA y gestión de sesiones.
- Revisar CORS, CSP, cookies, cabeceras y almacenamiento privado.
- Validar archivos, permisos, tamaño y contenido.
- No exponer secretos ni datos personales.
- Evitar sanitización universal destructiva.
- Registrar y probar controles de seguridad reales.

## Roles y pruebas
- Inventariar roles, permisos y alcances reales sin inventarlos.
- Automatizar pruebas parametrizadas de RBAC, ownership y sucursales.
- Probar permisos permitidos, denegados, revocados y expirados.
- Mantener E2E por perfiles relevantes.
- Verificar CRUD y flujos completos entre módulos.
- No considerar completa una función solo porque existe una vista, botón o modelo.
- Ejecutar lint, checks, migraciones y pruebas proporcionales al riesgo.
- Conservar pruebas de regresión y documentar skips.

## Documentación
- Mantener README.md profesional, actualizado y segmentado.
- Documentar arquitectura, tecnologías, funcionalidades, seguridad, base de datos, roles, APIs, integraciones, despliegue y testing.
- Explicar mecanismos, dependencias, librerías y limitaciones con evidencia del código.
- Mantener documentación modular sin duplicaciones innecesarias.
- Diferenciar implementado, probado, pendiente, deshabilitado y no aplicable.
- Actualizar documentación afectada por cada cambio.
- Usar código y pruebas como fuente técnica principal.

## Comentarios del código
- Todo archivo fuente propio compatible debe incluir encabezado descriptivo de su propósito.
- Comentar secciones relevantes de HTML, CSS, JS, Python, Docker y configuraciones.
- Explicar componentes, responsive, lógica, validaciones y decisiones técnicas importantes.
- Utilizar docstrings en funciones y clases complejas.
- Emplear lenguaje técnico preciso, conciso y profesional.
- Evitar comentarios triviales, redundantes, demostrativos u obsoletos.
- Respetar sintaxis, shebang, encoding, directivas y parsers.
- No insertar comentarios en JSON estricto, binarios ni archivos incompatibles.
- Excluir dependencias, generados y migraciones históricas protegidas.
- No modificar comportamiento solo para documentar.
- Mantener comentarios sincronizados con el código.

## Limpieza
- Auditar MD, TXT, logs, reportes y otros archivos históricos.
- Clasificar como vigente, reemplazable, histórico, temporal o dudoso.
- Crear documentación actualizada antes de eliminar versiones obsoletas.
- Comprobar referencias y dependencias antes de borrar.
- Conservar archivos esenciales, licencias, migraciones y backups necesarios.
- No eliminar cambios ajenos ni alterar historial Git.
- Registrar eliminaciones relevantes y justificación.

## Datos y presentación
- Sustituir textos demostrativos visibles por datos configurados o textos neutrales.
- No inventar empresas, direcciones, propietarios ni información real.
- Conservar fixtures sintéticos identificados como pruebas.
- No modificar datos reales sin autorización.
- No crear cuentas, vehículos u otros registros adicionales salvo solicitud expresa.

## Testeo beta
- Mantener guías en `docs/testeo-beta/`, con nombres `testeo-<rol-o-modulo>.md`.
- Generarlas según roles, permisos y funciones verificadas.
- Cada caso debe incluir ID, precondiciones, pasos, resultado esperado, estado, evidencia y observaciones.
- Cubrir CRUD, errores, restricciones, permisos y flujos entre módulos.
- Incluir ficha de evaluador, fecha, rol, versión, entorno y dispositivo.
- No almacenar cédulas completas ni datos sensibles en Git público.
- Mantener resultados individuales separados de las guías maestras.
- Relacionar casos manuales con pruebas automatizadas cuando existan.
- No inventar aprobaciones ni confundir beta testing con certificación oficial.

## Git y cierre
- Verificar rama, commit y cambios locales antes de trabajar.
- Preservar modificaciones ajenas y `web_carros/`.
- Commits independientes por bloque validado.
- No usar force push ni reescribir historial.
- Push solo a rama y remoto autorizados.
- No hacer merge, despliegue ni cambios de producción sin autorización.
- Entregar resumen breve: cambios, pruebas, commits, riesgos y pendientes.
- No declarar PRODUCTION READY sin verificaciones operativas y aprobación requerida.