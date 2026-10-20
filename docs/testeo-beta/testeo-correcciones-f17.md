# Testeo beta — correcciones F17

## Registro de la ejecución

Complete estos datos antes de probar. No incluya contraseñas, tokens, cédulas completas ni información real de clientes.

| Campo | Valor |
|---|---|
| Evaluador |  |
| Fecha |  |
| Versión / commit |  |
| Entorno |  |
| Navegador y versión |  |
| Dispositivo / resolución |  |
| Rol o permisos |  |

## Objetivo

Comprobar manualmente las correcciones F17 de contacto, obligatoriedad contextual, solicitudes comerciales, códigos VNV, canje sin kilometraje, administración vehicular, ayuda versionada, navegación responsive y consistencia entre datos mostrados y persistidos.

## Requisitos previos

- Entorno local, QA o staging autorizado; nunca producción para estas mutaciones.
- Dos clientes y dos vehículos sintéticos claramente diferenciados, en dos sucursales cuando se compruebe alcance.
- Una cuenta cliente con `portal.access`, un usuario con los permisos Staff indicados y otro sin ellos.
- Módulo postventa ON únicamente para los casos que lo requieren.
- Capturas o videos redactados; use los [mapas funcionales](../mapas-funcionales/README.md) como referencia de ubicación, no como resultado manual.

En esta guía, RBAC significa control de acceso basado en roles. El acceso a datos propios, también llamado *ownership*, exige que cada cliente vea únicamente su expediente y recursos vinculados.

## Casos

| ID | Flujo | Precondiciones | Pasos numerados | Resultado esperado observable | Resultado obtenido | Estado | Evidencia | Observaciones |
|---|---|---|---|---|---|---|---|---|
| FCR-001 | Teléfono y WhatsApp | Cuenta de prueba y formularios de registro/perfil disponibles. | 1. Escriba letras en teléfono y WhatsApp. 2. Intente guardar. 3. Corrija con un número sintético válido y guarde de nuevo. 4. Recargue la pantalla. | El servidor rechaza letras con un mensaje claro; el valor válido persiste sin modificar otros campos. |  | pendiente |  |  |
| FCR-002 | Canal preferido | Perfil cliente editable. | 1. Elija teléfono sin proporcionar teléfono e intente guardar. 2. Repita con WhatsApp y correo. 3. Elija atención presencial dejando esos datos vacíos. | Solo el dato correspondiente al canal elegido se vuelve obligatorio; presencial no exige un teléfono inventado. |  | pendiente |  |  |
| FCR-003 | Contacto entre módulos | Permisos para clientes y leads; formulario público accesible. | 1. Pruebe el mismo teléfono inválido en cliente Staff, lead, solicitud y perfil. 2. Pruebe un nombre Unicode válido. 3. Pruebe caracteres de control o un nombre incompatible. | Las superficies aplican la misma regla de contacto; tildes y ñ válidas se conservan, entradas incompatibles se rechazan sin escritura parcial. |  | pendiente |  |  |
| FCR-004 | Auditor heredado | Copia QA con al menos un registro sintético inválido conocido. | 1. Registre los conteos iniciales. 2. Ejecute `python manage.py audit_contact_data`. 3. Revise que solo informe modelo, identificador interno y campo. 4. Compare los datos después. | El comando identifica el registro sin imprimir su valor ni modificarlo; los conteos y contenido permanecen iguales. |  | pendiente |  |  |
| FCR-005 | Solicitud comercial | Portal público y límites de rate limiting disponibles. | 1. Sin iniciar sesión, envíe una solicitud con `5 usd`. 2. Pruebe más de dos decimales y un monto superior a `9.999.999.999,99`. 3. Envíe un Decimal válido con consentimiento y canal coherente. | Texto, precisión y exceso se rechazan; el Decimal válido crea solo una captura de interés, no reserva, cotización, factura ni pago. No se exige un mínimo comercial no aprobado. |  | pendiente |  |  |
| FCR-006 | Formato VNV | Código sintético vigente emitido desde la ficha Staff. | 1. Copie el código emitido. 2. Péguelo sin guiones en el formulario cliente. 3. Edite un carácter y use teclado para corregir. 4. Pruebe un código con tres grupos. | La entrada muestra `VNV-XXXX-XXXX-XXXX-XXXX`, permite edición normal y el backend rechaza formatos distintos al emisor real. |  | pendiente |  |  |
| FCR-007 | Canje sin kilometraje | Cuenta cliente con expediente activo, permiso y vehículo aún no vinculado. | 1. Abra “Agregar vehículo”. 2. Confirme que no existe campo de kilometraje. 3. Canjee el código válido. 4. Reintente el mismo código y pruebe abrir el vínculo desde el segundo cliente. | El primer canje vincula el vehículo sin pedir kilometraje; el reuso falla controladamente y el otro cliente no accede. Un kilometraje desconocido se muestra como “No registrado”, no como cero. |  | pendiente |  |  |
| FCR-008 | Multimedia y ficha | Usuario con `vehicles.manage` y vehículo sintético dentro de su sucursal. | 1. Suba un archivo permitido. 2. Edite texto alternativo, orden y visibilidad. 3. Cree/edite un destacado y una especificación. 4. Desvincule cada elemento y recargue. | Cada cambio persiste y queda auditado; quitar multimedia no borra el recurso reutilizable; archivo o relación ajenos se rechazan. |  | pendiente |  |  |
| FCR-009 | Identidad y estado vehicular | Dos sucursales; vehículos disponible, reservado y vendido. | 1. Cambie color o descripción ordinaria. 2. Intente cambiar VIN, marca, modelo o año sin justificación. 3. Repita con motivo en el vehículo disponible. 4. Intente en reservado/vendido y sobre vehículo de otra sede. | El campo ordinario cambia; la identidad exige motivo, queda auditada y solo cambia en estado permitido; estado o sede ajenos se deniegan. |  | pendiente |  |  |
| FCR-010 | Permiso de ayuda | Usuario con `help.manage`, usuario con solo `help.view` y Staff sin ambos. | 1. Abra la biblioteca con los tres usuarios. 2. Abra la URL de gestión directamente. 3. Intente crear desde las cuentas no autorizadas. | Lectores ven solo contenido permitido; solo `help.manage` abre y modifica la gestión; `is_staff` no concede el permiso. |  | pendiente |  |  |
| FCR-011 | Versiones de ayuda | Usuario con `help.manage` y artículo sintético. | 1. Cree el artículo con texto `<script>` literal. 2. Previsualice, publique y edite. 3. Despublíquelo y compruebe la biblioteca. 4. Restaure una versión anterior y abra el historial. | El texto no se ejecuta, el borrador no aparece a lectores y cada acción crea auditoría/versión; restaurar añade una versión sin borrar historia. |  | pendiente |  |  |
| FCR-012 | Navegación pública | Sesión anónima y viewports 320, 768, 1024, 1180 y 1440 px. | 1. Abra portada e instituciones en cada ancho. 2. Abra/cierre el menú con mouse y teclado. 3. Pulse Escape y cambie de ancho con el menú abierto. | No hay solapamiento ni scroll horizontal; todos los enlaces siguen accesibles, Escape cierra y el foco vuelve al disparador. |  | pendiente |  |  |
| FCR-013 | Navegación portal | Cuenta cliente; viewports 390, 768, 980 y 1440 px. | 1. Recorra dashboard, perfil, vehículos, servicios, documentos, facturas y notificaciones. 2. Abra el sidebar móvil. 3. Use overlay, Escape y teclado. 4. Pulse el logo. | El drawer no deja controles fuera de lienzo, bloquea el fondo mientras está abierto, restaura foco y el logo vuelve al hub público. |  | pendiente |  |  |
| FCR-014 | Navegación Staff | Usuario con nombre largo y permisos representativos; viewports 320, 768, 1024 y 1440 px. | 1. Recorra dashboard, inventario, ventas, vehículo y ayuda. 2. Abra/cierre sidebar y menú de usuario. 3. Confirme acceso con teclado. | Nombre y acciones se contienen o truncan sin ocultar funciones ni ampliar la página; los enlaces siguen sujetos a RBAC. |  | pendiente |  |  |
| FCR-015 | Consistencia y mapas | Datos sintéticos conocidos y acceso a las pantallas documentadas. | 1. Registre los valores fuente de un vehículo, orden, factura, stock y sede. 2. Compare cada pantalla con los [mapas funcionales](../mapas-funcionales/README.md). 3. Cambie un dato por su interfaz autorizada. 4. Recargue las vistas relacionadas y pruebe un estado vacío. | Etiquetas, cifras y relaciones corresponden al dato persistido o cálculo documentado; el cambio autorizado se refleja y el vacío no inventa información. |  | pendiente |  |  |

## Checklist de cierre

- [ ] `FCR-001` tiene estado y resultado obtenido.
- [ ] `FCR-002` tiene estado y resultado obtenido.
- [ ] `FCR-003` tiene estado y resultado obtenido.
- [ ] `FCR-004` tiene estado y resultado obtenido.
- [ ] `FCR-005` tiene estado y resultado obtenido.
- [ ] `FCR-006` tiene estado y resultado obtenido.
- [ ] `FCR-007` tiene estado y resultado obtenido.
- [ ] `FCR-008` tiene estado y resultado obtenido.
- [ ] `FCR-009` tiene estado y resultado obtenido.
- [ ] `FCR-010` tiene estado y resultado obtenido.
- [ ] `FCR-011` tiene estado y resultado obtenido.
- [ ] `FCR-012` tiene estado y resultado obtenido.
- [ ] `FCR-013` tiene estado y resultado obtenido.
- [ ] `FCR-014` tiene estado y resultado obtenido.
- [ ] `FCR-015` tiene estado y resultado obtenido.
- [ ] Cada fallo tiene incidencia separada y pasos reproducibles.
- [ ] Se comprobó validación de servidor, no solo máscaras de JavaScript.
- [ ] Se intentó acceso a un cliente, vehículo o sede ajenos sin conceder permisos adicionales.
- [ ] Las evidencias no exponen datos personales, archivos privados, claves ni códigos VNV vigentes fuera de QA.
- [ ] Se distinguieron pruebas automatizadas, ejecución humana y gates externos.

## Resultado de esta ejecución

- Incidencias:
- Bloqueos externos:
- Riesgos observados:
- Conformidad: `conforme` / `con reservas` / `no conforme`.
- Firma o referencia del evaluador (fuera del repositorio si contiene datos personales):
