# Matriz de compatibilidad LITE → PRO

Fecha de corte: 2026-10-09. Estados: **COMPLETO**, **PARCIAL**, **AUSENTE**, **INCOMPATIBLE**, **SUPERADO**. “COMPLETO” significa que existe un flujo equivalente utilizable, no solo un modelo o template. La evidencia PRO incluye el árbol actual sin commit; véase la nota de integración al final.

| Funcionalidad | Archivos LITE | Archivos PRO | Estado | Diferencias verificadas | Acción propuesta | Prioridad |
|---|---|---|---|---|---|---|
| Login usuario/correo | `routes/public_auth.py:98-167`, `core.py:1982-2036` | `accounts/backends.py`, `accounts/views.py:35-54`, `security_center/rate_limit.py` | SUPERADO | PRO usa caché compartida, bloqueo de cuenta, 2FA y política de seguridad. | Conservar; redirigir cliente al portal. | P0 |
| Registro público | `routes/public_auth.py:351-446` | `accounts/client_services.py`, vistas de registro e invitación | COMPLETO | Registro configurable e invitación de un uso concilian User, Customer y rol cliente. | Cerrado en B1. | P0 |
| Recuperación de contraseña | `routes/public_auth.py:170-349` | Vistas Django de reset, correo y token de un uso | COMPLETO | Respuesta anti-enumeración y rate limit compartido. | Cerrado en B1. | P0 |
| Cambio de contraseña, 2FA y sesiones | No hay cambio autenticado; sesión Flask básica | `security_center/urls.py:9-16`, `views.py:206-244` | SUPERADO | PRO agrega controles no presentes en LITE. | Reutilizar en configuración del portal. | P1 |
| Roles y permisos | `core.py:1836-1909` | `accounts/models.py`, `permissions.py`, `scopes.py` | SUPERADO | PRO usa permisos por código, vigencia y sucursal. | `portal.access` como puerta; ownership adicional en cada selector. | P0 |
| Cuenta ↔ expediente cliente | `usuarios` reúne identidad y cuenta | `Customer.account`, servicios de alta/invitación | COMPLETO | Separación preservada; vinculación valida rol, cuenta y unicidad, con auditoría. | Cerrado en B1. | P0 |
| Validación cédula/RUC | `core.py:1072-1179` | `common/validators.py`, `customers/identification.py` | SUPERADO | PRO aplica modelo/form/servicio y dedupe. | Reutilizar; no editar identificación desde portal. | P1 |
| Dashboard cliente | `routes/perfil.py:9-361`, `templates/profile.html:158-370` | `apps/portal`, shell privado y dashboard | COMPLETO | Portal responsive con ownership Customer y navegación por capacidades. | Cerrado en B2/B8. | P0 |
| Resumen y actividad reciente | `profile.html:166-365` | `portal_dashboard_data()` y actividad transversal | COMPLETO | Agregación privada optimizada, con presupuesto frío de 32 consultas. | Cerrado en B8. | P1 |
| Mis vehículos | `perfil.py:11-75`, `profile.html:374-452` | Portal garaje sobre `CustomerVehicle` | COMPLETO | Lista, búsqueda, paginación y ownership por vínculo activo. | Cerrado en B3. | P0 |
| Detalle privado de vehículo | `profile.html:1100-1297` | Detalle portal, medios públicos y VIN enmascarado | COMPLETO | Solo expone la unidad del Customer autenticado y recursos autorizados. | Cerrado en B3. | P1 |
| Código VNV y canje | `core.py:1687`, `perfil.py:982-1174` | `VehicleLinkCode`, `redeem_link_code()` y portal | SUPERADO | Servicio atómico, permiso de portal, restricción de dueño activo e idempotencia. | Cerrado en B0/B3. | P0 |
| Revocar/desvincular/transferir | `admin.py:1243-1469` | `vehicles/services.py:367-535`, vistas Staff | SUPERADO | PRO conserva historial y snapshots, con autorización y concurrencia cubiertas. | Cerrado en B0. | P0 |
| Catálogo público de vehículos | `routes/catalogo.py:20-407` | `vehicles/views.py:37-129`, `selectors.py` | COMPLETO | PRO tiene modelo rico, slug, medios y analítica. | Conservar; añadir enlace al garaje cuando autentique. | P2 |
| Imágenes/3D del vehículo | `core.py:1702-1769`, preview catálogo | `VehicleResource`, `VehicleMedia`, `VehiclePartSpecification` | SUPERADO | PRO separa recursos, medios, visibilidad y especificaciones. | Reutilizar; no duplicar assets en portal. | P2 |
| Historial de mantenimiento | `perfil.py:82-154`, `profile.html:516-604` | Portal sobre `ServiceOrder` y `ServiceOrderHistory` | COMPLETO | Aísla por Customer y vínculo activo; omite borradores internos. | Cerrado en B4. | P1 |
| Próximos servicios | `core.py:1235-1327`, `perfil.py:156-186` | Cita y recomendación explícita en `ServiceOrder` | COMPLETO | Muestra datos ingresados por personal sin scheduler ni avisos automáticos. | Cerrado en B4. | P1 |
| Registro/recepción por personal | `perfil.py:532-906` | Formulario operacional de `ServiceOrder` | SUPERADO | Incluye km recepción/entrega, diagnóstico y próxima atención validada. | Cerrado en B4. | P1 |
| Anulación/cancelación de servicio | `perfil.py:909-969` | transición auditada a `CANCELLED` | COMPLETO | Motivo obligatorio, actor y fecha explícitos. | Cerrado en B4. | P1 |
| Manuales del vehículo/modelo | `manuales_modelo`, `admin.py:2086-2171` | `ReusableAsset` publicado por modelo/año y portal | COMPLETO | Publicación controlada y descarga privada auditada. | Cerrado en B5. | P1 |
| Descarga segura de documentos | Facturas privadas seguras; manuales públicos | endpoints Staff/portal y `PrivateMediaStorage` | SUPERADO | Descarga autenticada, ownership, auditoría, `no-store` y storage privado. | Cerrado en B5/B9. | P0 |
| Documentos del cliente | Implícitos en manuales/facturas | biblioteca portal sobre `PrivateDocument` | COMPLETO | Filtra Customer, vínculo activo, estado y confidencialidad. | Cerrado en B5. | P1 |
| Facturas, líneas y estados | `facturas_vehiculo`, `factura_articulos` | `InvoiceRecord`, `InvoiceLine`, pagos e historial | SUPERADO | PRO usa Decimal, secuencia única y lifecycle consistente. | Reutilizar sin copiar cálculo LITE. | P1 |
| Facturas en portal | `perfil.py:230-255`, `profile.html:706-747` | lista y detalle privados del portal | COMPLETO | Estados autorizados y aislamiento por `invoice.customer`. | Cerrado en B6. | P1 |
| PDF de factura | `services/facturas.py:30-240` | PDF determinista enlazado a `PrivateDocument` | COMPLETO | Artefacto privado idempotente, sin pretensión SRI. | Cerrado en B6. | P2 |
| Descarga de factura propia | `routes/facturas.py:439-472` | endpoint portal con ownership | COMPLETO | Descarga auditada con `no-store`. | Cerrado en B6. | P1 |
| Bandeja cliente | `perfil.py:364-459`, `services/notificaciones.py` | portal sobre destinatarios Customer y User | COMPLETO | Unifica ambos tipos sin filtrar mensajes de otras cuentas. | Cerrado en B7. | P1 |
| Leer/archivar notificación | Rutas de perfil con `usuario_id` | servicios reutilizados por portal | COMPLETO | Operaciones limitadas al destinatario autenticado. | Cerrado en B7. | P1 |
| Marcar todas leídas | `perfil.py:398-425` | endpoint POST del portal | COMPLETO | Bulk limitado, CSRF y auditoría. | Cerrado en B7. | P2 |
| Preferencias de notificación | `perfil.py:462-517` | `CustomerNotificationPreference` | COMPLETO | Categorías empresariales sin recordatorios automáticos. | Cerrado en B7. | P2 |
| Eventos de negocio | Correos al registrar/canjear/facturar | eventos transaccionales post-commit | COMPLETO | Canje, documento, factura y estado de orden con deduplicación. | Cerrado en B7. | P2 |
| Avatar local | LITE depende de Cloudinary | `User.avatar`, vistas y validadores | SUPERADO | PRO soporta local seguro, reemplazo y borrado. | Mantener como fallback obligatorio. | P1 |
| Avatar Cloudinary | `perfil.py:1177-1243`, SDK fijado | adaptador, SDK de producción y healthcheck | COMPLETO LOCAL | CRUD simulado y fallo controlado validados; ciclo real queda como check externo de staging. | Cerrado en B9, pendiente proveedor real. | P2 |
| Edición de datos de perfil | LITE muestra datos; edita foto y preferencias | formulario Customer del portal | COMPLETO | Solo contacto/dirección; identidad y campos internos permanecen bloqueados. | Cerrado en B2. | P2 |
| Configuración de cuenta | Toggles visuales + logout | portal, preferencias, 2FA, sesiones y avatar | SUPERADO | Configuración persistente y seguridad real en shell coherente. | Cerrado en B2/B7. | P2 |
| Búsqueda local en garaje | `script1.js:120-139` | búsqueda server-side y paginación portal | COMPLETO | Accesible y sin exposición de unidades ajenas. | Cerrado en B3/B8. | P3 |
| Búsqueda Staff cliente/vehículo | AJAX LITE sin sucursal | `common/search.py`, selectors de customers/vehicles | SUPERADO | PRO añade filtros, límites, paginación y scoping. | Reutilizar para soporte; no exponer al cliente. | P2 |
| Inventario y stock por sucursal | `routes/articulos.py` | `apps/inventory/` | SUPERADO | PRO tiene modelos y permisos empresariales. | No mezclar con portal propietario salvo catálogo público futuro. | P3 |
| Catálogo público de repuestos | `/articulos` | `InventoryItem.is_public`, sin vista pública | PARCIAL | Base de datos existe, experiencia pública no. | Fase separada posterior al portal; no bloquear integración. | P3 |
| Directorio y mapa de sedes | `routes/instituciones.py`, MapTiler | `Branch`, home parcial | PARCIAL | Branch carece de coordenadas/horarios/servicios; sin mapa. | Integración pública posterior y opcional. | P3 |
| Contacto público | `public_auth.py:8-95` | `leads/PublicLeadRequestView` | SUPERADO | PRO integra el contacto al CRM y rate limit. | Conservar. | P3 |
| Correo transaccional | SMTP propio con modo simulado | Backend Django SMTP, reset e invitaciones | SUPERADO | Reset anti-enumeración, activación e invitaciones usan tokens de un uso; eventos del portal son idempotentes. | Cerrado en B1/B7. | P1 |
| Storage privado local | `private/facturas` | `PrivateMediaStorage` | COMPLETO | PRO generaliza a documentos privados. | Mantener y compartir servicio de descarga. | P0 |
| Storage privado externo | No existe | adaptador S3-compatible privado | SUPERADO | URL firmada, cifrado, timeout, healthcheck y fallback local explícito. | Cerrado en B9; ciclo real pendiente en staging. | P2 |
| Auditoría | `auditoria_acciones` best-effort | `AuditLog` con snapshots/hash | SUPERADO | — | Registrar todas las acciones nuevas del portal. | P0 |
| Módulos deshabilitables | Monolítico | Solo `post_sales` por setting | PARCIAL | No hay catálogo general persistido. | El portal debe degradar por capacidades; no crear multi-tenancy. | P1 |
| UI responsive y CSS | CSS por página, varios monolitos | `static/css/ui/` modular y estilos de portal | SUPERADO | Shell privado validado en móvil/tablet/escritorio, teclado y contraste AA. | Cerrado en B2/B8/B11. | P1 |
| SRI | LITE no lo implementa de forma válida | `apps/sri_integration/` | INCOMPATIBLE con alcance | El encargo excluye reintroducirlo. | No tocar ni conectar desde esta integración. | Fuera |
| Recordatorios automáticos de mantenimiento | Flag y cálculo en LITE, sin scheduler real | No existen | INCOMPATIBLE con alcance | Fueron descartados expresamente. | No implementar scheduler, Celery beat ni campañas automáticas de recordatorio. | Fuera |

## Reglas de negocio que cambian

- **Identidad:** en PRO `User` autentica y `Customer` es el expediente; nunca fusionarlos ni usar cédula como credencial.
- **Propiedad:** el acceso nace de `Customer.account` + `CustomerVehicle.is_active`; un permiso de portal sin ownership no autoriza datos.
- **Servicios:** `ServiceOrder` sustituye `mantenimientos`; no crear un segundo modelo histórico.
- **Facturas:** `InvoiceRecord` sustituye `facturas_vehiculo`; no portar floats, número editable ni estados inconsistentes.
- **Documentos:** `PrivateDocument` es la fuente para archivos confidenciales; una URL de media no es autorización.
- **Notificaciones:** `NotificationRecipient` es la fuente; se añade resolución Customer→account, no una tabla paralela.
- **Sucursales:** los procesos Staff conservan scoping; el cliente solo ve la sede asociada a sus registros, nunca datos internos de otras sedes.
- **Módulos:** `post_sales` OFF debe ocultar historial/servicios con estado vacío informativo o 404 según ruta; nunca romper el resto del portal.

## Nota sobre el cierre

Los bloques B0-B9 y B11 están confirmados en commits independientes de `integration/lite-pro`. Las dos brechas públicas P3 —catálogo de repuestos y mapa/directorio ampliado de sedes— quedan como producto posterior y no forman parte del portal privado ni de su aceptación. B10 continúa omitido: no se importaron datos históricos de LITE. Los gates que requieren proveedores o infraestructura reales se enumeran en `06-cierre-integral.md`.
