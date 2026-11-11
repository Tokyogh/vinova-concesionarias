# B2 — Comparación integral VINOVA LITE vs VINOVA PRO

Fecha de corte: 2026-10-15
Referencia: `web_carros/` en modo de solo lectura
Inventario LITE comprobado: 74 archivos, 68 decoradores Flask y 66 endpoints efectivos; dos reglas son alias.

## Convención

- **PARIDAD VERIFICADA:** el resultado útil existe en PRO y conserva la experiencia o el contrato relevante.
- **MEJORADO EN PRO:** existe el flujo y agrega controles o capacidades empresariales justificadas.
- **PARCIAL:** solo parte del flujo está disponible.
- **AUSENTE:** una capacidad útil de LITE no tiene equivalente operativo.
- **DIFERENTE JUSTIFICADO:** PRO resuelve el objetivo de otra forma por arquitectura o seguridad.
- **DEFECTUOSO:** el equivalente existe, pero falla de forma reproducible.
- **EXCLUIDO EXPRESAMENTE:** no debe integrarse por decisión de alcance.

## Matriz por flujo

| Área / acción LITE | Implementación LITE | Equivalente PRO | Validaciones, permisos y persistencia | Clasificación |
|---|---|---|---|---|
| Inicio público | `/`, HTML monolítico y datos SQLite. | Hub público modular, catálogo, servicios, nosotros, contacto e instituciones. | Templates autoescapados, settings empresariales y assets versionados. | **MEJORADO EN PRO** |
| Contacto | `POST /contacto`, correo y registro local. | `leads:public_request` crea Lead con validación y rate limit. | Servicio CRM, transacción, CSRF y límites por ventana. | **MEJORADO EN PRO** |
| Login | `/login` con sesión Flask. | Backend email/usuario, bloqueo, política de contraseña, sesión y 2FA. | Rate limit, historial de contraseña y security profile. | **MEJORADO EN PRO** |
| Recuperación | Token propio `/recuperar` y `/restablecer/<token>`. | Flujo Django anti-enumeración y tokens de un uso. | No revela existencia de cuenta; SMTP parametrizado. | **MEJORADO EN PRO** |
| Registro cliente | `POST /register` crea usuario/identidad en la misma estructura. | Registro/invitación, `User` separado de `Customer` y asociación explícita. | No vincula por coincidencia simple de correo, cédula o nombre. | **DIFERENTE JUSTIFICADO** |
| Logout | `POST /logout`. | `accounts:logout` POST. | CSRF y cierre de sesión. | **PARIDAD VERIFICADA** |
| Shell cliente | `/perfil`, sidebar, topbar y diez secciones. | `/mi-cuenta/`, misma jerarquía, 260 px, tarjetas, cuadrícula, modal y responsive. | Datos vienen de selectors PRO con ownership. | **PARIDAD VERIFICADA** |
| Dashboard cliente | Métricas, actividad y gráfica. | Métricas, serie de seis meses, actividad y alertas. | Agregaciones acotadas al Customer resuelto. | **PARIDAD VERIFICADA** |
| Garaje | Lista, búsqueda, ficha y modal de cuatro pestañas. | Lista/paginación, búsqueda y detalle progresivo con cuatro pestañas. | `CustomerVehicle.is_active`; VIN y datos privados no cruzan owners. | **PARIDAD VERIFICADA** |
| Canje de vehículo | Código VNV y kilometraje. | `redeem_link_code()` con código normalizado y vínculo CustomerVehicle. | Advisory lock, `select_for_update`, unicidad e idempotencia funcional. | **MEJORADO EN PRO** |
| Reversión/traspaso | LITE revierte canje mediante flags. | Desvinculación y transferencia conservan snapshots e historial. | Permiso `vehicles.link_codes`, branch scope y auditoría sensible. | **MEJORADO EN PRO** |
| Reactivar código revocado | LITE vuelve a habilitar una fila de código. | PRO no reutiliza códigos: genera uno nuevo y revoca cualquier activo anterior. | Reduce reutilización accidental; usado/revocado nunca vuelve a activo. | **DIFERENTE JUSTIFICADO** |
| Historial técnico | Servicios realizados/anulados por vehículo. | ServiceOrder e historial de transiciones por vehículo. | Ownership y flag `post_sales`; estados no borrador. | **MEJORADO EN PRO** |
| Próximo servicio | Fecha/km derivados; parte del recordatorio era visual. | Fecha y kilometraje almacenados y mostrados cuando existen. | No inventa scheduler ni avisos automáticos. | **DIFERENTE JUSTIFICADO** |
| Manuales | PDF/imagen por modelo/año desde static. | ReusableAsset publicado y descarga controlada desde portal. | Storage privado/público según recurso, alcance y auditoría. | **MEJORADO EN PRO** |
| Facturas cliente | Listado, estado y archivo privado. | InvoiceRecord, líneas, pagos, detalle y PDF determinista. | Decimal, secuencias, ownership y `no-store`. | **MEJORADO EN PRO** |
| Perfil/avatar | Datos de usuario y foto, con Cloudinary opcional. | Contacto Customer, identidad bloqueada y avatar local/Cloudinary validado. | Tipo, dimensiones, tamaño, reemplazo y borrado controlados. | **MEJORADO EN PRO** |
| Notificaciones cliente | Leer, ocultar, marcar todas y preferencias. | Bandeja, detalle, leer todas, archivar y preferencias. | Recipient por User/Customer, CSRF, bulk acotado y auditoría. | **PARIDAD VERIFICADA** |
| Configuración de cuenta | Toggles visuales y salida. | Preferencias persistentes, contraseña, 2FA, sesiones y avatar. | Backend real; los controles no son decorativos. | **MEJORADO EN PRO** |
| Panel administrador | Una pantalla monolítica para todas las áreas. | Módulos separados y navegación declarativa. | RBAC granular y alcance por sucursal. | **DIFERENTE JUSTIFICADO** |
| Panel trabajador | Rol único con conjunto fijo de acciones. | Trece roles combinables con permisos vigentes y branch scope. | Deny-by-default en vista, selector y servicio. | **MEJORADO EN PRO** |
| Usuarios y roles | Crear usuario, cambiar rol/estado, asignar establecimiento. | CRUD, roles múltiples, vigencia, activación y sucursal por UserRole. | `accounts.manage_users/assign_roles`; global o scoped. | **MEJORADO EN PRO** |
| Vehículos internos | Crear/editar, imagen, 3D, estado, archivo y borrado. | CRUD, media, recursos, publicación, archive y permiso de borrado permanente. | Validación de archivo, soft delete y permisos separados. | **MEJORADO EN PRO** |
| Catálogo público vehículos | `/catalog`, preview y ficha. | `/vehicles/`, filtros, orden, slug, detalle, galería, favoritos locales y analytics. | Solo publicados/activos; sin datos privados. | **MEJORADO EN PRO** |
| Inventario interno | Artículos, stock, movimientos y transferencias. | Items, BranchStock y ledger StockMovement. | Bloqueo de filas, validación y branch scope. | **MEJORADO EN PRO** |
| Mínimo/ubicación de stock | Editable en gestión LITE. | Servicio `update_minimum_stock()` sin UI/API consumidora. | Servicio tiene permiso, lock, validación y auditoría. | **PARCIAL** |
| Catálogo público de repuestos | `GET /articulos` con imagen y disponibilidad. | No existe pantalla pública equivalente. | Los modelos internos no deben exponerse sin reglas de publicación/precio/stock. | **AUSENTE** |
| Facturación operativa | Crear factura, cambiar estado y ver archivo. | Venta→InvoiceRecord, acciones, pagos, impresión y PDF. | Estados estrictos, Decimal, permisos y auditoría. | **MEJORADO EN PRO** |
| Mantenimientos Staff | Alta, búsqueda y anulación. | Postventa modular, líneas, estados e historial. | ON/OFF, permisos, branch scope y transacción. | **MEJORADO EN PRO** |
| Instituciones públicas | Tres categorías, cards, lista, mapa, detalle y filtros. | `/instituciones/` replica estructura, interacción, MapLibre/MapTiler y fallback. | Solo empresa/sede activas y públicas; coordenadas opcionales y CSP acotada. | **PARIDAD VERIFICADA** |
| Datos de sede | Nombre, tipo, dirección, ciudad/provincia, contacto, horario, servicios, lat/lng. | Branch cubre esos campos y formulario/API los validan. | ORM, rangos geográficos y servicio auditado. | **PARIDAD VERIFICADA** |
| Imagen y website de sede | Imagen validada y URL website por establecimiento. | No existen campos ni pipeline por sede; se usan imágenes estáticas por categoría. | No se copió el storage público inseguro de LITE. | **PARCIAL** |
| Reparación automática de coordenadas | LITE ejecuta UPDATE y asigna coordenadas de fallback. | PRO conserva `NULL`, mantiene la sede en lista y solicita coordenadas verificadas. | Evita representar una ubicación inventada como real. | **DIFERENTE JUSTIFICADO** |
| Manuales Staff | Alta/estado dentro del panel monolítico. | Biblioteca de assets reutilizables y publicación. | Permisos y storage especializado. | **MEJORADO EN PRO** |
| Mensajería Staff | Buscar destinatarios y enviar. | Notificaciones, plantillas y campañas segmentadas. | Scope, consentimiento, snapshots y deduplicación. | **MEJORADO EN PRO** |
| Storage | Archivos en `static/` y carpeta privada ad hoc. | Adaptadores local, Cloudinary y S3-compatible privado. | Descarga autorizada, URL firmada, timeout y fallback. | **MEJORADO EN PRO** |
| Auditoría | Tabla/log best-effort y SQL directo. | AuditLog con snapshots, hashes, request id y alertas. | Servicio transversal y consulta restringida. | **MEJORADO EN PRO** |
| API e integraciones | No existe API empresarial equivalente. | DRF, clientes API, scopes, idempotencia, webhooks, OpenAPI y BI. | Bearer hasheado, throttling, SSRF guard y branch filter. | **MEJORADO EN PRO** |
| Privacidad | No hay módulo sistemático. | Consentimientos, solicitudes, export, retención y anonimización. | Permisos separados y auditoría. | **MEJORADO EN PRO** |
| Continuidad/QA | Scripts/manuales puntuales. | Backups, restore drills, update center y runner QA persistente. | Permisos, storage privado, flags y colas. | **MEJORADO EN PRO** |
| SRI | LITE no ofrece una integración válida. | Existe app desacoplada en PRO. | El encargo prohíbe reintroducirla o ampliarla. | **EXCLUIDO EXPRESAMENTE** |
| SaaS/multi-tenant | No aplica en LITE. | No hay tenant middleware; Company es configuración organizacional. | Una instalación corresponde a una organización. | **EXCLUIDO EXPRESAMENTE** |
| Recordatorios automáticos de mantenimiento | Cálculos/flags parciales sin scheduler fiable. | No implementados. | Exclusión explícita; tampoco deben dispararse desde campañas/Celery. | **EXCLUIDO EXPRESAMENTE** |

## Cobertura de las 68 reglas Flask

El código LITE no cambió y se reconfirmaron sus 68 decoradores. Esta auditoría
corrige las conclusiones históricas que quedaron obsoletas:

| Reglas LITE | Cobertura actual PRO | Resultado B2 |
|---|---|---|
| 1–7: público/autenticación | Hub, Lead público, login/reset/registro/logout. | Paridad o mejora; registro diferente por separación User/Customer. |
| 8–19: portal cliente | Shell, notificaciones, postventa, canje y avatar. | Paridad funcional/visual o mejora; recordatorios automáticos excluidos. |
| 20–41: administración | Dashboards y módulos accounts/vehicles/customers/documents/branches/notifications. | Mejora modular; la regla 31 no equivale a reactivar: PRO emite código nuevo. |
| 42–51: trabajador | Dashboard por rol y operaciones scoped. | Mejora por RBAC; no existe rol monolítico obligatorio. |
| 52–62: artículos/inventario | Gestión interna cubierta; público no. | Regla 52 **AUSENTE**; mínimo de stock **PARCIAL**; resto mejora. |
| 63–64: catálogo vehículo | Catálogo, detalle, media y specs. | Mejora. |
| 65–67: facturas | Ciclo y PDF privado. | Mejora. |
| 68: instituciones | Directorio y mapa restaurados. | Paridad, salvo imagen/website propios. |

## Diferencias de seguridad que no deben copiarse

- SQL manual y reparaciones implícitas de datos en solicitudes GET.
- Identidad, cuenta y expediente mezclados en una sola fila.
- Archivos cargados dentro de `static/` y autorización basada en conocer la URL.
- Reutilización de códigos revocados.
- Roles `admin`/`trabajador` demasiado amplios y sin vigencia granular.
- Estados y totales financieros menos estrictos o basados en representaciones no decimales.
- Mutaciones y ownership resueltos dentro de rutas monolíticas en lugar de servicios/selectores.

PRO conserva ORM, servicios transaccionales, permisos, branch scope, ownership, CSRF, archivos privados y auditoría como fuente de verdad.

## Brechas priorizadas

| ID | Brecha | Impacto | Prioridad | Decisión de B2 |
|---|---|---|---|---|
| B2-01 | Catálogo público de repuestos. | Capacidad visible de LITE ausente; requiere definir publicación, precios y exposición de stock. | P3 | Documentar como desarrollo de producto separado; no improvisar en esta auditoría. |
| B2-02 | Imagen/website por institución. | Directorio usa imagen genérica y no ofrece enlace web propio. | P2 | Evaluar en B3; implica modelo, storage, validación y administración, no un parche visual. |
| B2-03 | Edición de mínimo/ubicación de BranchStock. | Servicio correcto sin interfaz consumidora. | P2 | Candidato a defecto puntual de integración en B3. |
| B2-04 | Documentos antiguos afirman que instituciones siguen pendientes y que códigos se reactivan. | Estado y decisiones incorrectos para operación/testers. | P1 documental | Sustituir/corregir en B6–B7, preservando historia cuando corresponda. |

## Conclusión B2

No se detectó una función esencial del portal privado LITE ausente en PRO. La paridad del portal y del directorio público está verificada localmente con las diferencias seguras descritas. Permanecen una capacidad pública nueva no autorizada para implementación (`/articulos`), dos brechas parciales de administración y exclusiones explícitas. No hay un hallazgo **DEFECTUOSO** adicional confirmado en este bloque.
