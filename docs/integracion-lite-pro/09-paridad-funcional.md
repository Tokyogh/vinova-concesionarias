# 09 — Auditoría de paridad funcional LITE → PRO

Fecha de corte: 2026-10-12. Referencia LITE auditada en modo solo lectura. Estados: `COMPLETO`, `PARCIAL`, `AUSENTE`, `INCOMPATIBLE`, `SUPERADO`.

## Resultado ejecutivo

- Se confirmaron **68 reglas Flask / 66 endpoints**. El inventario fuente y sus líneas está en `docs/vinova-redesign/reference-inventory.md`.
- La lógica empresarial útil del portal privado está cubierta por modelos y servicios PRO; no se detectó una necesidad legítima de duplicar tablas LITE.
- La brecha P0 encontrada es de experiencia: PRO ofrece las áreas como páginas independientes y no reproduce todavía el shell, densidad, distribución, gráfica ni modal de `profile.html`.
- Las diferencias públicas ya declaradas (repuestos públicos y mapa de sedes) permanecen P3. SRI, multi-tenant y recordatorios automáticos siguen fuera del alcance acordado.
- La seguridad de PRO se conserva como fuente de verdad: `Customer.account`, permiso vigente `portal.access`, vínculos activos y selectors con ownership.

## Matriz funcional profunda

| Área | Función LITE | Evidencia LITE | Equivalente PRO | Evidencia PRO | Diferencia | Severidad | Acción | Prueba |
|---|---|---|---|---|---|---|---|---|
| Acceso | Login, recuperación, registro y logout | `routes/public_auth.py:98-446`; `routes/logout.py:3` | Backend de cuenta, rate-limit, tokens e invitación cliente | `apps/accounts/backends.py`; `apps/accounts/views.py`; `apps/accounts/client_services.py` | PRO añade 2FA, sesiones y política | SUPERADO | Conservar | pruebas accounts/security |
| Ownership | Usuario LITE contiene identidad y expediente | `routes/perfil.py:9` | Cuenta separada de `Customer`; expediente activo/VIP | `apps/portal/selectors.py:portal_customer_for_user` | Diseño más seguro; requiere asociación explícita | SUPERADO | Conservar servicio de vinculación auditado | regresión de clientes heredados |
| Inicio | Cuatro métricas, garaje, próximos servicios, gráfica, actividad | `profile.html:158-370`; `perfil.py:9-361` | Agregación privada de todos los dominios | `portal_dashboard_data`; `portal_recent_activity` | Falta composición/gráfica visual equivalente | P0 PARCIAL | Restaurar layout y serie de 6 meses | DOM, queries y visual |
| Vehículos | Galería, búsqueda local, ficha y modal con cuatro pestañas | `profile.html:374-452,1100-1297`; `script1.js` | Lista, detalle, medios, ficha técnica, VIN protegido | `portal_vehicle_links_queryset`; `PortalVehicleDetailView` | Detalle abre página y no modal equivalente | P1 PARCIAL | Shell/modal progresivo sin relajar ownership | E2E + acceso horizontal |
| Canje | Código VNV, km inicial y transacción exclusiva | `perfil.py:982-1174` | Servicio atómico idempotente | `apps/vehicles/services.py:redeem_link_code`; `PortalVehicleRedeemView` | Sin diferencia funcional relevante | SUPERADO | Reutilizar | concurrencia/idempotencia |
| Historial | Servicios realizados/anulados por vehículo | `profile.html:516-604`; `perfil.py:82-154` | Órdenes no borrador e historial de transición | `portal_service_orders_queryset`; `ServiceOrderHistory` | Presentación separada | COMPLETO | Integrar apariencia LITE | filtros/ownership |
| Próximos servicios | Próxima fecha/km y estado derivado | `core.py:1235-1327`; `profile.html:611-652` | `scheduled_at`, `next_service_date`, `next_service_mileage` | `apps/post_sales/models.py:33-42`; portal services | PRO no inventa scheduler automático | COMPLETO | Mostrar explícitamente fecha y km disponibles | estados vacíos |
| Manuales | Manual por modelo/año | `profile.html:659-699`; `manuales_modelo` | Assets publicados por modelo/año/sucursal | `portal_manuals_queryset`; descarga auditada | PRO restringe publicación y descarga | SUPERADO | Conservar | ownership/descarga |
| Documentos | Documentos implícitos en manuales/facturas | `profile.html:659-747` | Biblioteca privada general | `portal_private_documents_queryset` | Capacidad adicional | SUPERADO | Mostrar junto a manuales sin mezclar scopes | acceso horizontal |
| Facturas | Lista, estado, total y PDF privado | `profile.html:706-747`; `routes/facturas.py` | Factura, líneas, pagos, PDF determinista | `portal_invoices_queryset`; `ensure_invoice_pdf` | PRO usa Decimal y ciclo más estricto | SUPERADO | Conservar | detalle/PDF/ownership |
| Perfil | Identidad, contacto y fotografía | `profile.html:752-877`; `perfil.py:1177-1243` | Contacto editable, identidad bloqueada, avatar validado | `PortalProfileView`; `AvatarUploadForm` | PRO evita editar identidad sensible | SUPERADO | Integrar visualmente | validación/auditoría |
| Notificaciones | Bandeja, leer, ocultar, leer todas, preferencias | `profile.html:884-1051`; `perfil.py:364-517` | Recipient por Customer/User, leer, archivar y preferencias | selectors/services de notifications; portal views | Ocultar se representa como archivar | COMPLETO | Mantener semántica auditable | CSRF/ownership/bulk |
| Configuración | Toggles visuales y salida | `profile.html:1058-1090` | Preferencias persistentes, contraseña, 2FA y sesiones | `PortalSettingsView`; security center | PRO convierte controles decorativos en reales | SUPERADO | Integrar en shell | persistencia/seguridad |
| Personal | Alta/anulación de mantenimiento | `perfil.py:532-969` | Órdenes de servicio y transiciones auditadas | `apps/post_sales/services.py` | Modelo más completo | SUPERADO | No exponer mutación Staff al cliente | permisos/sucursal |
| Administración | Vehículos, usuarios, códigos, manuales y sedes | `routes/admin.py` | Módulos accounts, vehicles, customers, documents, branches | apps homónimas | Arquitectura modular y permisos granulares | SUPERADO | No duplicar UI dentro del portal | suites de módulos |
| Trabajador | Operación acotada de vehículos/clientes/notificaciones | `routes/trabajador.py` | RBAC + scope de sucursal | `apps/accounts/scopes.py`; vistas internas | PRO elimina rol monolítico | SUPERADO | Conservar | pruebas de permisos/scope |
| Inventario | Artículos, stock, transferencias y movimientos | `routes/articulos.py` | Inventario por sucursal y ledger | `apps/inventory` | Catálogo público de repuestos aún no existe | P3 PARCIAL | Fase pública separada | inventario/concurrencia |
| Catálogo | Vehículos públicos y preview técnico | `routes/catalogo.py` | Catálogo rico, medios, slugs y analytics | `apps/vehicles/views.py`; selectors | Sin brecha útil | SUPERADO | Conservar | catálogo público |
| Sedes | Directorio y mapa MapTiler | `routes/instituciones.py`; `instituciones.js` | `Branch` y presencia parcial pública | `apps/branches`; home | Faltan coordenadas/mapa/horarios equivalentes | P3 PARCIAL | Producto público posterior | pendiente deliberado |

## Cobertura explícita de las 68 reglas LITE

Cada fila identifica la regla original y su destino. Dos reglas alias explican la diferencia entre 68 reglas y 66 endpoints.

| # | Regla LITE | Destino PRO | Estado |
|---:|---|---|---|
| 1 | `GET /` | `dashboard:home` | SUPERADO |
| 2 | `POST /contacto` | `leads:public_request` | SUPERADO |
| 3 | `GET/POST /login` | `accounts:login` | SUPERADO |
| 4 | `POST /recuperar` | `accounts:password_reset` | SUPERADO |
| 5 | `GET/POST /restablecer/<token>` | reset confirm Django | SUPERADO |
| 6 | `POST /register` | registro/invitación cliente | COMPLETO |
| 7 | `POST /logout` | `accounts:logout` | COMPLETO |
| 8 | `GET /perfil` | `portal:dashboard` y diez áreas | PARCIAL visual |
| 9 | `POST /perfil/notificaciones/<id>/leer` | detalle marca lectura | COMPLETO |
| 10 | `POST /perfil/notificaciones/marcar-todas` | `portal:notification_read_all` | COMPLETO |
| 11 | `POST /perfil/notificaciones/<id>/ocultar` | `portal:notification_archive` | COMPLETO |
| 12 | `POST /perfil/notificaciones` | `portal:settings` | COMPLETO |
| 13 | `POST /perfil/mantenimiento/registrar` (stub) | orden de servicio interna real | SUPERADO |
| 14 | `POST /perfil/mantenimiento/<id>/eliminar` (stub) | transición cancelada real | SUPERADO |
| 15 | `GET /mantenimientos/buscar-vehiculos` | búsqueda Staff con scope | SUPERADO |
| 16 | `POST /mantenimientos/registrar` | alta de `ServiceOrder` | SUPERADO |
| 17 | `POST /mantenimientos/<id>/anular` | cancelación auditada | SUPERADO |
| 18 | `POST /perfil/vehiculo/agregar` | `portal:vehicle_redeem` | SUPERADO |
| 19 | `POST /perfil/foto` | `accounts:avatar_update` | SUPERADO |
| 20 | `GET /admin` | dashboard interno | SUPERADO |
| 21 | `GET /admin/vehiculos` | vehicles internal list | SUPERADO |
| 22 | `POST /admin/vehiculos/guardar` | create/update vehicle | SUPERADO |
| 23 | `POST /vehiculos/guardar` (alias) | create/update vehicle | SUPERADO |
| 24 | `POST /admin/vehiculos/<id>/estado` | transición de inventario | SUPERADO |
| 25 | `POST /admin/vehiculos/<id>/codigo/generar` | generar `VehicleLinkCode` | SUPERADO |
| 26 | `POST /admin/vehiculos/<id>/archivar` | soft-delete/estado | SUPERADO |
| 27 | `POST /admin/vehiculos/<id>/desarchivar` | restauración controlada | SUPERADO |
| 28 | `POST /admin/vehiculos/<id>/eliminar-permanente` | borrado protegido por servicio | SUPERADO |
| 29 | `POST /admin/canjes/<id>/reversar` | revocar vínculo con snapshot | SUPERADO |
| 30 | `POST /admin/codigos/<id>/desactivar` | revocar código | SUPERADO |
| 31 | `POST /admin/codigos/<id>/reactivar` | reactivar código válido | SUPERADO |
| 32 | `POST /admin/usuarios/crear` | accounts/customers services | SUPERADO |
| 33 | `POST /admin/usuarios/<id>/rol` | RBAC asignación vigente | SUPERADO |
| 34 | `POST /admin/usuarios/<id>/estado` | activación de cuenta | SUPERADO |
| 35 | `GET /admin/notificaciones/buscar-usuarios` | selectors de destinatarios | SUPERADO |
| 36 | `POST /admin/notificaciones/enviar` | notifications service | SUPERADO |
| 37 | `POST /admin/trabajadores/<id>/establecimiento` | scope/branch de cuenta | SUPERADO |
| 38 | `POST /admin/establecimientos/guardar` | branches create/update | SUPERADO |
| 39 | `POST /admin/establecimientos/<id>/estado` | branch state | SUPERADO |
| 40 | `POST /admin/manuales/guardar` | reusable assets | SUPERADO |
| 41 | `POST /admin/manuales/<id>/estado` | publicación de asset | SUPERADO |
| 42 | `GET /trabajador` | dashboard por permisos | SUPERADO |
| 43 | `GET /trabajador/notificaciones/buscar-clientes` | búsqueda con scope | SUPERADO |
| 44 | `POST /trabajador/notificaciones/enviar` | notifications service | SUPERADO |
| 45 | `POST /trabajador/vehiculos/<id>/estado` | vehicle service + permiso | SUPERADO |
| 46 | `POST /trabajador/vehiculos/<id>/desarchivar` | vehicle service + permiso | SUPERADO |
| 47 | `POST /trabajador/vehiculos/<id>/codigo/generar` | link-code service | SUPERADO |
| 48 | `POST /trabajador/vehiculos/<id>/archivar` | vehicle service + permiso | SUPERADO |
| 49 | `POST /trabajador/codigos/<id>/reactivar` | link-code service | SUPERADO |
| 50 | `POST /trabajador/usuarios/crear` | accounts/customers services | SUPERADO |
| 51 | `POST /trabajador/usuarios/<id>/cedula` | identificación validada | SUPERADO |
| 52 | `GET /articulos` | no hay catálogo público de repuestos | PARCIAL P3 |
| 53 | `GET /articulos/api/gestion` | inventory internal selectors/API | SUPERADO |
| 54 | `GET /articulos/buscar-factura` | selección de líneas de factura | SUPERADO |
| 55 | `POST /articulos/guardar` | inventory create/update | SUPERADO |
| 56 | `POST /articulos/transferir-stock` | transferencia transaccional | SUPERADO |
| 57 | `POST /articulos/<id>/estado` | inventory state | SUPERADO |
| 58 | `POST /articulos/<id>/archivar` | soft-delete | SUPERADO |
| 59 | `POST /admin/articulos/<id>/eliminar-permanente` | borrado protegido | SUPERADO |
| 60 | `GET /admin/vehiculos/ocultos/api` | inventory/vehicle selectors | SUPERADO |
| 61 | `GET /inventario/vehiculos/ocultos/api` (alias) | inventory/vehicle selectors | SUPERADO |
| 62 | `POST /inventario/vehiculos/<id>/activar` | transición de inventario | SUPERADO |
| 63 | `GET /catalog` | `vehicles:catalog` | SUPERADO |
| 64 | `POST /catalog/vehiculos/<id>/preview/guardar` | specs/media internas | SUPERADO |
| 65 | `POST /facturas/guardar` | invoice service | SUPERADO |
| 66 | `POST /admin/facturas/<id>/estado` | lifecycle de factura | SUPERADO |
| 67 | `GET /facturas/<id>/ver` | detalle/descarga portal privada | SUPERADO |
| 68 | `GET /instituciones` | branches/presencia pública parcial | PARCIAL P3 |

## Geometría y comportamiento del portal de referencia

- `profile.html`: 10 secciones, shell lateral, topbar, cuatro tarjetas, cuadrícula 2×2 y modal de vehículo con pestañas Resumen/Historial/Mantenimiento/Documentación.
- Escritorio 1440×900 medido: sidebar `260×900`, `position: sticky`, padding `25px`; documento inicial `1440×1106`, sin overflow horizontal.
- PRO antes de la restauración: contenido centrado `1180px`, navegación superior `1180×60`, documento inicial `1440×1742`; la divergencia es estructural, no solo cromática.
- Evidencia reproducible: `scripts/ui/portal_parity.py`; PNG y JSON quedan en `run/portal-parity/` (no versionados y sin credenciales).

## Decisiones seguras de integración

1. No copiar SQL, modelos ni autenticación de LITE.
2. Reutilizar exclusivamente selectors y servicios PRO para toda lectura/mutación.
3. Replicar estructura, jerarquía, dimensiones, navegación y estados vacíos del frontend LITE usando tokens de color PRO.
4. Mantener rutas profundas para enlaces, accesibilidad y degradación sin JavaScript; la presentación puede abrirlas en el shell/modal sin cambiar ownership.
5. No declarar paridad total mientras `10-paridad-visual.md` conserve diferencias P0/P1 o los gates externos sigan pendientes.
