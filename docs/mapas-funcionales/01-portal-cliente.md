# Mapa funcional — Portal cliente

## Límite de acceso común

Todas las pantallas privadas parten de `PortalCustomerRequiredMixin` y `portal_customer_for_user`. La cuenta debe estar autenticada, activa, conservar `portal.access` vigente y estar vinculada explícitamente mediante `Customer.account` a un expediente no borrado con estado `ACTIVE` o `VIP`. La ausencia de expediente produce una respuesta controlada; no se busca ni vincula por correo, cédula o nombre.

La raíz de ownership es siempre el `Customer` resuelto. Los selectores añaden condiciones por cliente y, cuando corresponde, por `CustomerVehicle.is_active`; no aceptan identificadores ajenos sin volver a aplicar ese alcance.

## Trazabilidad por pantalla

| Captura y componente | Fuente y transformación | Modificación autorizada | Vacío, permisos y prueba |
|---|---|---|---|
| [01](capturas/01-dashboard-cliente.png) — resumen | `portal_dashboard_data`: cuenta `CustomerVehicle` activos, documentos, manuales, facturas y notificaciones no leídas; `portal_recent_activity` une actividad limitada y ordenada. | Las tarjetas son de lectura; cada dominio conserva sus propias vistas y servicios. | Sin datos muestra estados vacíos del template. Requiere el límite común. Cubierto por `apps/portal/tests/` y el escenario visual F17. |
| [02](capturas/02-indicadores-mantenimiento.png) — mantenimiento | `portal_service_orders_queryset` filtra `ServiceOrder` del cliente y de un vehículo con vínculo activo, excluye `DRAFT`; `_portal_service_chart` agrega completados de seis meses y normaliza altura contra el máximo. | No se edita una orden desde el portal. Staff opera el dominio postventa mediante sus permisos. | El bloque desaparece si el módulo `post_sales` está OFF; sin órdenes se conservan cero/estado vacío. Hay regresión específica de módulo OFF. |
| [03](capturas/03-perfil-cliente.png) — perfil | `PortalCustomerProfileForm` proyecta los datos de contacto del expediente y aplica validadores compartidos de nombres, teléfono, WhatsApp y canal preferido. | El propio cliente guarda sus datos mediante `PortalProfileView`; no puede cambiar ownership, roles ni sucursal. | Errores se presentan en el formulario, sin persistencia parcial. Requiere `portal.access` y expediente elegible. Cubierto por pruebas F17 de contacto. |
| [04](capturas/04-mis-vehiculos.png) — garaje | `portal_vehicle_links_queryset` lee `CustomerVehicle` activos del cliente, excluye vehículos borrados y precarga marca, modelo, sede y medios públicos. La búsqueda se normaliza con `clean_search_query`. | La ficha es de lectura. La vinculación se realiza únicamente mediante código privado o por una operación Staff autorizada. | Sin vínculos muestra garaje vacío. `portal_vehicle_link_detail` vuelve a filtrar por cliente, evitando acceso horizontal. |
| [05](capturas/05-vinculacion-codigo.png) — canje VNV | `PortalVehicleRedeemForm` normaliza y valida el formato emitido `VNV-XXXX-XXXX-XXXX-XXXX`; el servicio `redeem_link_code` valida vigencia, uso y vínculo. El formulario no acepta kilometraje del cliente. | El cliente canjea el código; la emisión/revocación corresponde a `vehicles.link_codes`. | Código inválido, vencido, revocado o ya usado devuelve error controlado. La operación es transaccional y está cubierta por pruebas de concurrencia e idempotencia. |
| [06](capturas/06-historial-servicios.png) — servicios | `portal_service_orders_queryset` permite búsqueda y estado sobre el conjunto propio; la vista separa próximas órdenes e historial. Los importes, fechas y kilometrajes proceden de `ServiceOrder`. | Lectura cliente; las mutaciones siguen en postventa Staff. | Módulo OFF bloquea incluso URL directa. Un vehículo de otro cliente no amplía el queryset. |
| [07](capturas/07-documentos.png) — documentos | `portal_private_documents_queryset` incluye `PrivateDocument` activos asignados al cliente o genéricos de un vehículo actualmente propio; un documento de cliente anterior nunca sigue al vehículo. | Descarga mediante vista privada y auditable; el cliente no altera metadatos. | Excluye borrados/inactivos y responde 404 dentro del alcance ante ID ajeno. Las descargas y ownership tienen regresiones de seguridad. |
| [07b](capturas/07b-facturas.png) — facturas | `portal_invoices_queryset` filtra `InvoiceRecord.customer`, excluye borrados y borradores, precarga líneas y aplicaciones de pago. | Lectura y descarga; emisión, pagos y anulaciones requieren servicios Staff. | Lista vacía controlada. `portal_invoice_detail` vuelve a aplicar el selector propio. |
| [08](capturas/08-notificaciones.png) — mensajes | `portal_notifications_queryset` reúne `NotificationRecipient` dirigido al `Customer` o a su `account`, exige mensaje enviado y no borrado, y excluye archivados salvo solicitud explícita. | El destinatario puede marcar leído, archivar y actualizar preferencias mediante servicios dedicados. | No aparecen borradores ni destinatarios ajenos. Los filtros se aplican después del ownership. |

## Modelos y campos principales

- `Customer.account`, `Customer.status`, `Customer.is_deleted`: vínculo explícito y elegibilidad.
- `CustomerVehicle.customer`, `is_active`, `vehicle`: ownership del garaje.
- `ServiceOrder.customer`, `vehicle`, `status`, `scheduled_at`, `completed_at`, `next_service_date`, `next_service_mileage`: mantenimiento.
- `PrivateDocument.customer`, `vehicle`, `status`, `is_deleted`: alcance documental.
- `InvoiceRecord.customer`, `status`, `is_deleted`: comprobantes.
- `NotificationRecipient.customer`, `user`, `recipient_type`, `status`: destinatario y estado.

La evidencia visual usa dos órdenes, un documento, una factura y una notificación sintéticos. No acredita proveedores externos ni resultados manuales de beta.
