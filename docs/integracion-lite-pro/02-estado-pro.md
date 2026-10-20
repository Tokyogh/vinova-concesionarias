# VINOVA PRO: estado actual frente al portal cliente

Fecha de corte: 2026-10-09. Esta auditoría describe el árbol de trabajo actual, incluidos cambios locales sin commit en cuentas, clientes y vehículos. `python manage.py check` terminó sin errores y `makemigrations --check --dry-run` indicó que no hay cambios de modelo sin migración; la comprobación de historia contra PostgreSQL no pudo ejecutarse porque el host Docker `db` no estaba disponible desde el host.

## 1. Arquitectura que se conserva

- Django 5.2, PostgreSQL, Redis/Celery, Django REST Framework y permisos propios por código (`config/settings/base.py:29-66`).
- 26 apps de negocio instaladas y 289 declaraciones `path()` entre configuración y apps. La arquitectura separa modelos, formularios, selectores, servicios, vistas, API y tests.
- Cuenta propia `accounts.User`, roles y permisos M2M con alcance opcional por sucursal: `apps/accounts/models.py` (`PermissionCode`, `Role`, `User`, `UserRole`).
- Scoping canónico por sucursal en `apps/accounts/scopes.py`; auditoría con hash encadenado en `apps/audit/`; validación y normalización común en `apps/common/`.
- Seguridad superior a LITE: CSRF de Django, política de contraseña, rate limit compartido por caché, bloqueo de cuenta, 2FA, sesiones revocables, CSP/cabeceras y auditoría.
- CSS existente dividido en tokens, componentes, páginas, temas y breakpoints (`static/css/ui/`), base correcta para un portal modular y responsive.
- No es SaaS. `Company` y `Branch` modelan la empresa instalada y sus sedes; la integración no debe introducir tenant middleware, selección de tenant ni partición multiempresa.

## 2. Cuentas, autenticación y perfiles

### Existente

- Login por usuario o correo, cuenta activa, rate limit en Redis/caché y bloqueo persistido: `apps/accounts/backends.py:13-61`, `apps/security_center/rate_limit.py`.
- Logout POST, perfil autenticado, avatar propio: `apps/accounts/urls.py:22-32`, `apps/accounts/views.py:35-107`.
- Cambio de contraseña autenticado, 2FA y administración de sesiones: `apps/security_center/urls.py:9-16`.
- Alta/edición, roles, activación y contraseña por personal: `apps/accounts/views.py:121-288`.
- Avatar validado con Pillow (JPG/PNG/WEBP, tamaño y dimensiones), sustitución y borrado; local por defecto o Cloudinary opcional: `apps/common/validators.py`, `apps/accounts/storage.py`, `apps/accounts/cloudinary_avatar.py`.
- Rol `cliente` y permiso `portal.access` declarados en `apps/accounts/management/commands/seed_roles.py:5-53`.

### Incompleto o ausente

- No hay registro público ni recuperación autoservicio. `apps/accounts/urls.py` solo publica login, logout, perfil y gestión interna; `templates/accounts/login.html:42-56` deriva el olvido de contraseña al administrador.
- `LOGIN_REDIRECT_URL` y `VinovaLoginView.get_success_url()` llevan al perfil básico si no hay panel interno, no a un dashboard cliente.
- `UserProfileView` solo añade roles y avatar (`apps/accounts/views.py:62-69`). No resuelve el expediente `Customer`, garaje, documentos, facturas ni notificaciones.
- `templates/accounts/profile.html:2-26` contiene HTML dentro del bloque `title` y repite la sección de seguridad; es un defecto de plantilla que debe corregirse antes de usarla como shell del portal.
- El cliente no puede editar teléfono, dirección, preferencia de contacto o datos del expediente. La identificación debe seguir siendo controlada y auditada por personal.

## 3. Cliente y asociación con cuenta

### Existente

- `Customer` cubre persona/empresa, identificación, contacto, sucursal, asesor, estado y notas (`apps/customers/models.py:8-111`).
- `Customer.account` es `OneToOneField` a `User` y evita que una cuenta represente dos expedientes (`apps/customers/models.py:49-56`).
- Gestión interna de cuenta asociada en `CustomerAccountLinkForm`, `InternalCustomerLinkAccountView` y `link_customer_account()` (`apps/customers/forms.py:203-215`, `apps/customers/views.py:116-131`, `apps/customers/services.py:179-192`).
- Validación EC, normalización y deduplicación están implementadas y auditadas.

### Brechas

- Vincular una cuenta no asigna ni comprueba el rol `cliente`/permiso `portal.access`; puede quedar una relación válida que no accede al canje.
- El selector ofrece cualquier usuario activo, incluidos usuarios internos. Falta una política explícita para evitar mezclar identidad de empleado y cliente salvo caso autorizado.
- No existe flujo de invitación/verificación de correo ni reconciliación segura entre registro público y un Customer ya creado por ventas.

## 4. Vehículos y garaje digital

### Existente en el árbol actual

- Catálogo y ficha pública, filtros, multimedia, 3D y especificaciones: `apps/vehicles/models.py:13-242`, `apps/vehicles/views.py:37-261`.
- Gestión interna con VIN, placa, código interno estable, estados, archivo y scoping.
- `VehicleLinkCode`: código aleatorio, estado, caducidad, uso, revocación y un código activo por vehículo (`apps/vehicles/models.py:245-315`).
- `CustomerVehicle`: titular/conductor, km inicial, vínculo activo, snapshots y fecha/motivo de desvinculación (`apps/vehicles/models.py:318-373`).
- Servicios transaccionales para generar, revocar, canjear, desvincular y transferir, con `select_for_update`, advisory lock y auditoría: `apps/vehicles/services.py:293-535`.
- Controles Staff y endpoint cliente `/vehicles/canjear/`: `apps/vehicles/internal_urls.py`, `apps/vehicles/urls.py:7-12`, `apps/vehicles/views.py:436-577`.
- Pruebas de formato, expiración, doble canje, reversa/transferencia y endpoint: `apps/vehicles/tests/test_garage.py`.

### Brechas

- No hay vista “mis vehículos” ni detalle privado; el endpoint de canje es una página aislada.
- El GET de `VehicleRedeemCodeView` exige login pero no valida `portal.access` ni cuenta Customer; esa validación ocurre solo en POST (`apps/vehicles/views.py:534-577`).
- La restricción DB asegura un vínculo activo por pareja cliente/vehículo, no un único propietario activo por vehículo. El servicio lo impide bajo bloqueo, pero conviene una restricción parcial adicional para defensa en profundidad.
- Las migraciones `customers.0003`, `vehicles.0006` y el permiso `accounts.0004` existen en cambios locales aún no confirmados; antes de construir el portal deben integrarse y verificarse en la rama objetivo.

## 5. Postventa, servicios e historial

### Existente

- `ServiceOrder`, líneas e historial de estados con cliente, vehículo, sucursal, responsable, agenda, costos Decimal y documentos: `apps/post_sales/models.py`.
- Selectores con scoping y servicios transaccionales/auditados: `apps/post_sales/selectors.py`, `apps/post_sales/services.py`.
- Interfaz Staff para lista, alta, detalle, transición y líneas: `apps/post_sales/urls.py` y `templates/post_sales/`.
- Módulo protegido por `OptionalModuleRequiredMixin` y deshabilitado por defecto con `VINOVA_MODULE_POST_SALES_ENABLED=False`: `apps/common/modules.py`, `config/settings/base.py:88`.

### Brechas

- No existe selector/vista de portal por `request.user.customer_profile`.
- `ServiceOrder` no registra km de recepción/entrega, diagnóstico, próxima fecha/km recomendada ni motivo estructurado de cancelación.
- No existe una programación de “próximos servicios” equivalente. Por requisito actual no debe reintroducirse un motor de recordatorios automáticos; la alternativa es mostrar citas y recomendaciones explícitas registradas por personal.
- El cierre de orden no crea ni enlaza automáticamente una factura, documento o notificación cliente.

## 6. Documentos, manuales y archivos

### Existente

- `PrivateDocument` relacionable con cliente, vehículo y venta, con metadatos, confidencialidad y almacenamiento fuera de `MEDIA_URL`: `apps/documents/models.py:72-137`, `apps/documents/storage.py`.
- Descarga Staff protegida, scoping por sucursal, `no-store` y auditoría: `apps/documents/views.py:110-143`, `apps/documents/selectors.py`.
- `ReusableAsset`, `VehicleResource` y `VehicleMedia` soportan manuales y recursos reutilizables (`apps/documents/models.py`, `apps/vehicles/models.py:48-75,181-205`).
- Validación de extensión/tamaño y hash de archivos.

### Brechas

- No hay descarga con ownership de cliente. La vista existente exige `documents.download_private`, un permiso Staff.
- Manuales no están asociados de forma reutilizable al modelo para aparecer automáticamente en todas sus unidades. Puede reutilizarse `VehicleResource` y su asociación, sin crear otra tabla de manuales como en LITE.
- `VehicleResource.file` y `ReusableAsset.file` usan el storage público por defecto. Para documentos del propietario debe usarse `PrivateDocument` o un backend privado con URL firmada.
- `PRIVATE_STORAGE_BACKEND` y variables S3 aparecen en settings de entorno, pero `PrivateMediaStorage` es local fijo; no hay implementación S3/R2/GCS conectada.

## 7. Facturas

### Existente y superior

- `InvoiceSequence`, `InvoiceRecord`, líneas, aplicaciones de pago e historial; Decimal, número único, impuestos, emisión, cobro y anulación: `apps/invoices/models.py`.
- Scoping por sucursal y flujos Staff: `apps/invoices/selectors.py`, `apps/invoices/services.py`, `apps/invoices/views.py`.
- Factura puede enlazar un `PrivateDocument` mediante `linked_document` (`apps/invoices/models.py:80`).

### Brechas

- No hay listado/detalle de facturas para el Customer autenticado.
- No hay PDF generado; `InvoicePrintView` solo renderiza HTML (`apps/invoices/views.py:175-181`).
- No hay endpoint de descarga del comprobante con ownership de cliente.
- No existe unión automática y transaccional ServiceOrder → InvoiceRecord → PrivateDocument. SRI existe como módulo empresarial separado, pero queda expresamente fuera de esta integración.

## 8. Notificaciones

### Existente y superior en Staff

- Mensajes, plantillas, destinatarios individuales, prioridades, tipos, relaciones de negocio, deduplicación, campañas, consentimiento y auditoría: `apps/notifications/models.py`, `services.py`.
- Bandeja para destinatarios `user`, lectura al abrir y archivo individual: `apps/notifications/selectors.py:49-62`, `apps/notifications/views.py:41-151`.
- Campañas por segmento y scoping de sucursal.

### Brechas cliente

- `NotificationRecipient` admite `customer`, pero `user_inbox_queryset()` filtra exclusivamente `user=user`; una campaña dirigida a Customer no aparece en la cuenta vinculada.
- Las vistas internas exigen `notifications.view`/`notifications.send`; el rol `cliente` solo tiene `portal.access`.
- No hay marcar-todas, preferencias por categoría ni contador en el navbar público.
- No hay eventos transaccionales para canje, factura, documento o cambio de orden. No se deben crear recordatorios automáticos de mantenimiento.

## 9. Empresa, módulos y configuración

- `CompanyPublicSettings` centraliza identidad, contacto, textos públicos y toggles de presentación (`apps/enterprise/models.py:10-55`).
- `ApprovalPolicy` cubre acciones empresariales; debe conservarse.
- El único módulo realmente deshabilitable es `post_sales`, mediante setting de entorno (`apps/common/modules.py`). No existe aún una matriz persistida de módulos por empresa.
- `Branch` no tiene latitud/longitud, horario, web, imagen ni servicios JSON (`apps/branches/models.py:6-30`); el directorio público actual es parcial y no tiene mapa.

## 10. Almacenamiento e integraciones

| Integración | Estado PRO | Evaluación |
|---|---|---|
| Cloudinary | Adaptador de avatar completo en código, con save/open/url/exists/delete/size y fallback local. | **Parcial operativo:** el paquete `cloudinary` no está en requirements y las variables `CLOUDINARY_*` no están documentadas en los `.env.*.example`; las pruebas usan SDK simulado. No se verificó proveedor real. |
| SMTP | Backend Django configurable en `config/settings/base.py:150-159`. | Base reutilizable; faltan reset público y pruebas de plantillas/entrega del portal. |
| Storage privado | Local fuera de media pública. Dependencias `boto3`/`django-storages` solo en producción. | Seguro localmente, pero el backend externo declarado no está conectado a `PrivateMediaStorage`. |
| PDF | No hay WeasyPrint/ReportLab en requirements. | Ausente para comprobante descargable. |
| MapTiler | Ausente; `Branch` carece de coordenadas. | No es requisito central del portal, pero sí paridad pública pendiente. |

## 11. Diagnóstico resumido

PRO ya supera a LITE en arquitectura, seguridad, permisos, scoping, auditoría, facturación, CRM, documentos y operación empresarial. La brecha no es falta de modelos empresariales: es la ausencia de una capa de portal que proyecte, con ownership de cliente, esos modelos existentes.

Estado del portal:

- **Listo para reutilizar:** login, perfil de seguridad, avatar local, Customer/account, garaje y canje, vehículos, facturas, documentos, ServiceOrder, notificaciones y permisos.
- **Parcial:** asociación cuenta-cliente, endpoint de canje, almacenamiento Cloudinary, postventa, manuales y módulo ON/OFF.
- **Ausente:** shell/dashboard cliente, autoservicio de registro/reset, mis vehículos, historial/proximidad, documentos/facturas del propietario, bandeja Customer, preferencias y configuración cliente.
