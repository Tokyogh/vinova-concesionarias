# Arquitectura de integración del portal cliente

## 1. Decisión principal

PRO sigue siendo la arquitectura y fuente de datos. LITE define los comportamientos que deben recuperarse, no el diseño técnico que se debe copiar.

Se propone una app de presentación/orquestación `apps.portal` sin duplicar dominios. El portal consumirá servicios y selectores de `accounts`, `customers`, `vehicles`, `post_sales`, `documents`, `invoices` y `notifications`.

```text
sesión Django
    |
    v
apps.portal (URLs, vistas, formularios, selectores de composición)
    |
    +-- Customer.account == request.user  [raíz obligatoria de ownership]
    |
    +-- vehicles.CustomerVehicle --------> vehicles.Vehicle / VehicleMedia
    +-- post_sales.ServiceOrder ----------> historial y citas/recomendaciones
    +-- documents.PrivateDocument --------> archivos privados autorizados
    +-- invoices.InvoiceRecord -----------> comprobantes del Customer
    +-- notifications.NotificationRecipient -> bandeja y preferencias
```

`apps.portal` no tendrá copias de Vehicle, ServiceOrder, InvoiceRecord, PrivateDocument o NotificationMessage. Toda mutación seguirá pasando por servicios de dominio y toda lectura por selectores con ownership explícito.

## 2. Frontera de acceso

### 2.1 Identidad efectiva

Un usuario es cliente de portal únicamente si cumple las tres condiciones:

1. Está autenticado y activo.
2. Tiene `portal.access` vigente.
3. Existe exactamente un `Customer` no borrado con `account=request.user`.

Un helper central `portal_customer_for_user(user)` resolverá esa identidad o denegará de forma uniforme. No se aceptará Customer ID desde querystring/form como autoridad.

### 2.2 Ownership por recurso

| Recurso | Regla de lectura cliente |
|---|---|
| Vehículo | `CustomerVehicle(customer=portal_customer, is_active=True)`. |
| Historial de servicio | `ServiceOrder.customer=portal_customer` y vehículo vinculado; una orden de otro dueño nunca se expone por compartir vehículo. |
| Cita/próximo servicio | Igual que historial y estado permitido; solo datos explícitos de la orden/recomendación. |
| Documento | `PrivateDocument.customer=portal_customer`; si tiene vehículo, además debe corresponder a un vínculo autorizado. |
| Manual reutilizable | Asociación publicada al vehículo/modelo propio; nunca documento confidencial ajeno. |
| Factura | `InvoiceRecord.customer=portal_customer`; solo estados de cliente y documento enlazado propio. |
| Notificación | Recipient con `customer=portal_customer` o `user=request.user`, nunca por email libre. |

Las vistas reciben PKs solo después de filtrar el queryset autorizado; un `get_object_or_404(Model, pk=...)` sin scope queda prohibido en el portal.

### 2.3 Transferencia de propiedad

- Desactivar el vínculo anterior preserva snapshots y fecha/motivo.
- La nueva titularidad no transfiere facturas, contratos, datos personales ni notificaciones.
- El historial técnico solo será visible si la orden está asociada al Customer actual o si en una fase futura se define un subconjunto explícitamente “transferible y sin datos personales”. La primera versión usa la regla estricta `ServiceOrder.customer=current_customer`.
- Añadir una restricción parcial de un único `CustomerVehicle` activo con rol `owner` por vehículo. El bloqueo transaccional existente se mantiene.

## 3. Rutas y experiencia

Rutas sugeridas:

```text
/mi-cuenta/                         dashboard
/mi-cuenta/vehiculos/               garaje
/mi-cuenta/vehiculos/canjear/       canje
/mi-cuenta/vehiculos/<id>/          detalle privado
/mi-cuenta/servicios/               historial y próximas atenciones
/mi-cuenta/documentos/              biblioteca propia
/mi-cuenta/documentos/<id>/descargar/
/mi-cuenta/facturas/                comprobantes
/mi-cuenta/facturas/<id>/
/mi-cuenta/notificaciones/          bandeja
/mi-cuenta/notificaciones/marcar-todas/
/mi-cuenta/perfil/                  datos editables
/mi-cuenta/configuracion/           avatar, preferencias y seguridad
```

`accounts:profile` puede redirigir a `portal:dashboard` para usuarios cliente y conservar el perfil actual para usuarios internos. El login resolverá el destino por capacidad: staff al dashboard interno, cliente al portal.

La navegación será server-rendered con mejora progresiva; no se requiere SPA ni API pública nueva. Esto reduce superficie de autorización. Los endpoints JSON, si se necesitan para filtros o contadores, aplicarán el mismo helper de ownership.

## 4. Modelos y migraciones mínimas

### 4.1 Reutilizados sin duplicación

- `accounts.User`, `Role`, `PermissionCode`, `UserRole`.
- `customers.Customer` y `Customer.account`.
- `vehicles.Vehicle`, `VehicleLinkCode`, `CustomerVehicle`, `VehicleMedia`, `VehicleResource`.
- `post_sales.ServiceOrder`, `ServiceOrderLine`, `ServiceOrderHistory`.
- `documents.PrivateDocument` y recursos existentes.
- `invoices.InvoiceRecord` y `linked_document`.
- `notifications.NotificationMessage` y `NotificationRecipient`.

### 4.2 Extensiones justificadas

1. `CustomerVehicle`: constraint parcial de propietario activo único por vehículo. No cambia el servicio existente; lo refuerza.
2. `ServiceOrder`: `reception_mileage`, `delivery_mileage`, `diagnosis`, `next_service_date`, `next_service_mileage`, `cancelled_at/by/reason`. Los campos de próxima atención son una recomendación escrita por personal, no un recordatorio automático.
3. `NotificationPreference`: OneToOne con Customer; canales/categorías `in_app`, `email`, `invoices`, `documents`, `service_updates`, `vehicle_alerts`. No incluir `automatic_maintenance_reminders`.
4. `CompanyPublicSettings`: `allow_client_registration` si la empresa desea habilitar autoservicio. Sigue siendo una sola empresa instalada.
5. Opcional `ClientInvitation`: Customer, email normalizado, token hasheado, expiración, uso y actor; solo si se implementa activación por invitación. Evita enlazar por coincidencia de email sin prueba.

No se propone una tabla nueva de mantenimiento, factura, manual, actividad o notificación.

## 5. Autenticación y vinculación segura

### Flujo preferido: invitación

1. Personal selecciona Customer y crea/asocia una cuenta mediante servicio transaccional.
2. El servicio garantiza email único, rol `cliente`, `portal.access`, y prohíbe reutilizar una cuenta Staff salvo confirmación y permiso superior.
3. Se envía enlace de activación de un uso y corta expiración; el token se almacena hasheado.
4. Cliente define contraseña y entra al portal.

### Registro público opcional

- Controlado por `allow_client_registration`, rate limit y verificación de correo.
- Crea `User` + `Customer` prospecto en una transacción solo cuando no hay conflicto.
- Si ya existe un Customer con ese correo/identificación, no se autoasocia ni se revela su existencia; se deriva al flujo de invitación/soporte.
- El código VNV sigue siendo la única prueba para agregar una unidad. Cédula, correo o placa no prueban propiedad.

### Recuperación

Usar vistas/formularios estándar de Django, respuesta anti-enumeración, token de un uso, expiración, plantillas propias y backend SMTP existente. Mantener cambio autenticado, 2FA y sesiones actuales.

## 6. Vehículos y canje

- Reutilizar `generate_vehicle_link_code`, `redeem_link_code`, `revoke_vehicle_link_code`, `unlink_customer_vehicle` y `transfer_customer_vehicle`.
- Mover la página aislada de canje al shell del portal o hacerla delegar al mismo formulario/servicio.
- Validar `portal.access` y Customer tanto en GET como POST.
- No cambiar automáticamente `Vehicle.status` a vendido al canjear: PRO conserva su lifecycle comercial. La vinculación representa propiedad/acceso, no sustituye la venta.
- Mostrar VIN de forma parcial si la política lo requiere; nunca exponer código de vinculación usado ni datos de propietarios históricos.

## 7. Servicios y próximos mantenimientos

El portal consulta `ServiceOrder`; no importa la tabla `mantenimientos` como modelo paralelo.

- Historial: órdenes completadas del Customer, con líneas, costos visibles, sede, fechas y documentos autorizados.
- Próximas atenciones: órdenes `scheduled` y recomendaciones `next_service_date/mileage` introducidas al cerrar una orden.
- Estado visual (`programado`, `próximo`, `vencido`) puede derivarse al leer, sin tarea programada y sin enviar mensajes automáticamente.
- Si `post_sales` está OFF, las rutas específicas responden 404 y el dashboard oculta el bloque o muestra “módulo no habilitado”; el resto del portal funciona.
- No crear Celery beat, campañas ni correos de recordatorio de mantenimiento.

## 8. Documentos, manuales y facturas

### Documentos

Extraer de `PrivateDocumentDownloadView` un servicio compartido que:

- recibe un documento ya autorizado;
- abre desde su storage sin construir paths manuales;
- registra descarga;
- devuelve `Content-Disposition`, MIME validado, `nosniff` y `Cache-Control: private, no-store`.

Staff y portal tendrán selectores distintos y usarán el mismo servicio de entrega.

### Manuales

No recrear `manuales_modelo`. Reutilizar `VehicleResource`/`VehicleMedia` o una asociación M2M mínima de `VehicleModel` a recursos existentes. Solo recursos publicados se muestran. Un manual confidencial se representa como `PrivateDocument`, no como media pública.

### Facturas

- Listar `InvoiceRecord` por Customer.
- Mostrar estados y montos del modelo empresarial; no copiar cálculo de LITE.
- Al emitir, generar un PDF desde datos persistidos, guardarlo como `PrivateDocument` tipo factura y asignarlo a `linked_document` dentro de una transacción/flujo idempotente.
- La descarga requiere simultáneamente factura propia y documento enlazado propio.
- No conectar ni modificar SRI.

## 9. Notificaciones

Crear selectores de portal sobre `NotificationRecipient`:

```text
Q(user=request.user) OR Q(customer=portal_customer)
```

Siempre validar que `recipient_type` y FK sean coherentes. Reutilizar `mark_recipient_read` y `archive_recipient`; añadir `mark_all_read(customer, user)` con una sola actualización limitada al queryset propio.

Los eventos permitidos son canje completado, documento disponible, factura emitida/anulada y cambio manual de una orden. Deben crearse con `transaction.on_commit`, `dedup_key` e idempotencia. Las preferencias se evalúan antes del canal de correo. No se emiten recordatorios automáticos.

## 10. Almacenamiento externo

### Avatar/Cloudinary

El adaptador actual implementa subida, URL, consulta, reemplazo y borrado. Para declararlo operativo faltan:

1. fijar una versión compatible del SDK `cloudinary` en requirements opcionales/de producción;
2. añadir solo los nombres `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` a ejemplos y documentación;
3. configurar `STORAGE_BACKEND=cloudinary` en staging;
4. prueba real de crear, leer URL, reemplazar, invalidar CDN y borrar;
5. health check no destructivo y observabilidad de fallback.

Local seguirá siendo fallback y entorno de pruebas. No registrar secretos ni URLs firmadas en logs.

### Documentos privados

Cloudinary no es el backend heredado para facturas/manuales privados. Mantener filesystem privado o conectar `PRIVATE_STORAGE_BACKEND` a un storage S3 compatible con bucket privado, cifrado, timeouts y URLs firmadas cortas. La vista de ownership sigue siendo obligatoria incluso si el proveedor firma URLs.

## 11. UI y CSS

- Shell propio de portal, formal y responsive, alineado con los tokens de `static/css/ui/tokens.css` y componentes existentes.
- Archivos sugeridos: `portal-shell.css`, `portal-dashboard.css`, `portal-vehicles.css`, `portal-records.css`, `portal-settings.css` y un breakpoint específico; no un único archivo monolítico.
- Componentes reutilizables: tarjetas métricas, estado, tabla/lista responsive, empty state, paginación, avatar y mensajes.
- Sin estética neón/gamer. Contraste AA, navegación por teclado, foco visible, landmarks, labels y mensajes de error asociados.
- Corregir primero el bloque `title` defectuoso de `templates/accounts/profile.html`.

## 12. Migración de datos LITE, si se autoriza

La integración funcional no exige importar el SQLite de LITE. Si se requiere conservar datos históricos, usar un importador idempotente y explícito, nunca ejecutar el SQLite como base de PRO:

| LITE | PRO | Regla |
|---|---|---|
| `usuarios` USUARIO | `User` + `Customer.account` | Match controlado por email/identificación; reporte de conflictos, sin fusión automática. |
| `vehiculos` | `Vehicle` | `codigo_catalogo`→`internal_code`; VIN nulo; normalizar estados. |
| `usuarios_vehiculos` | `CustomerVehicle` | Solo tras resolver Customer y Vehicle; preservar fecha/km/snapshot. |
| `mantenimientos` | `ServiceOrder` + history/lines | Mapear completados/anulados, Decimal y sede; conservar ID fuente en reporte o metadata de importación. |
| `facturas_vehiculo` | `InvoiceRecord` + `PrivateDocument` | Validar número, montos y archivo; no afirmar validez tributaria. |
| `manuales_*` | recursos existentes | Hash para dedupe; decidir publicación/confidencialidad. |
| `notificaciones_usuario` | message + recipient | Resolver Customer/cuenta; preservar lectura y fecha. |

Usar `apps.imports` como infraestructura de lote, checksum, prevalidación, confirmación y rollback lógico. El origen se abre en modo read-only. Ninguna migración se ejecuta automáticamente al desplegar el portal.

## 13. Riesgos críticos y mitigaciones

| Riesgo | Severidad | Mitigación verificable |
|---|---|---|
| Fuga horizontal de documentos/facturas/servicios | Crítica | Selector raíz por Customer, tests A/B para cada ruta y descarga, 404 en IDs ajenos. |
| Cuenta asociada sin permiso o cuenta Staff usada como cliente | Alta | Servicio único de asociación, rol/permiso atómico, validación de conflicto y auditoría. |
| Dos propietarios activos por carrera o escritura externa | Alta | Bloqueo actual + constraint parcial DB + test concurrente PostgreSQL. |
| Cambios R06 sin commit/migración en rama objetivo | Alta | Estabilizar y commitear antes de portal; `migrate --plan` y tests en PostgreSQL. |
| Documentos públicos por URL de media | Crítica | Privado fuera de media pública; entrega controlada o URL firmada corta; prueba de acceso directo. |
| Transferencia expone datos del dueño anterior | Crítica | No heredar Customer/documentos/facturas; tests de transferencia con dos clientes. |
| Cloudinary configurado pero SDK/credenciales ausentes | Media | Dependency pin, ejemplos de env, health check y smoke de staging; fallback explícito. |
| Storage externo declarado pero no conectado | Alta | Backend real para `PRIVATE_STORAGE_BACKEND` o eliminar promesa; prueba de save/open/delete. |
| PDFs no reproducibles o divergentes de la factura | Alta | Generar desde snapshot emitido, hash, idempotencia y golden tests de contenido básico. |
| Registro público crea duplicados o toma cuentas | Crítica | Verificación de email, no auto-link por coincidencia, rate limit e invitación preferida. |
| Módulo postventa OFF rompe dashboard | Media | Capability checks y tests ON/OFF en toda navegación/selector. |
| Regresiones en módulos empresariales | Alta | Portal aditivo, servicios existentes, suite por dominio y pruebas de permisos/scoping. |
| Reintroducción accidental de SRI o recordatorios | Alta | Exclusiones en criterios de aceptación y pruebas de ausencia de tareas/eventos automáticos. |

## 14. Criterios arquitectónicos de aceptación

- Ninguna entidad de negocio de LITE se duplica si PRO ya tiene equivalente.
- Todas las consultas cliente parten de `request.user.customer_profile` y tienen pruebas de aislamiento.
- Portal funciona con postventa OFF; no hay SRI ni recordatorios automáticos.
- Archivos confidenciales nunca se sirven desde una ruta pública predecible.
- Cada mutación sensible genera auditoría y es transaccional/idempotente donde aplica.
- Diseño responsive usa CSS modular y componentes existentes.
- La posible importación LITE es separada, reversible y nunca modifica `web_carros/`.
