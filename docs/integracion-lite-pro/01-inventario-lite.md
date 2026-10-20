# VINOVA LITE: inventario funcional y técnico

Fecha de corte: 2026-10-09. Fuente auditada en solo lectura: `web_carros/`. No se inspeccionaron valores de secretos ni datos personales. Las rutas de este documento son relativas a `web_carros/`.

## 1. Arquitectura y superficie

- Flask 3.1.3, Jinja2 y sesión firmada; aplicación global en `vinova/core.py:28-43` y registro de módulos de rutas en `app.py:1-13`.
- SQLite mediante `sqlite3` sin ORM (`vinova/core.py:169-175`), migraciones artesanales en `migrations/` y auto-creación puntual de notificaciones en `vinova/services/notificaciones.py:11-40`.
- 68 reglas Flask y 66 endpoints: `admin.py` 22, `articulos.py` 11, `catalogo.py` 2, `facturas.py` 3, `instituciones.py` 1, `logout.py` 1, `perfil.py` 12, `public_auth.py` 6 y `trabajador.py` 10.
- Interfaz monolítica: 10 plantillas, 8 archivos JS y 11 CSS. `templates/profile.html` concentra el portal; `admin.html` y `trabajador.html` concentran la operación interna.
- Dependencias distintivas: Cloudinary 1.44.2, Pillow 12.2, WeasyPrint 69.0 y SMTP estándar (`requirements.txt`).

La aplicación mezcla consultas SQL, reglas de negocio y presentación. Hay servicios separados para facturas, inventario, notificaciones y almacenamiento, pero la mayor parte de los flujos vive todavía en controladores extensos.

## 2. Datos y relaciones

El SQLite observado contiene 19 tablas funcionales. El DDL versionado no cubre todas las tablas legacy y `migrar_estructura_vinova.py` no forma parte del runner normal, por lo que el esquema real es una fuente de verdad adicional.

| Dominio | Tablas | Relación o finalidad |
|---|---|---|
| Identidad | `usuarios` | Cuenta, rol, foto, recuperación y cinco preferencias de notificación. |
| Vehículos | `vehiculos`, `vehiculo_modelos`, `codigos_vehiculo`, `usuarios_vehiculos`, `canjes_reversados` | Unidad, modelo compartido, código privado, titularidad y snapshot de reversa. |
| Postventa | `mantenimientos` | Servicio realizado, km, costo, próxima fecha/km y anulación. |
| Documentos | `manuales_modelo`, `manuales_vehiculo`, `facturas_vehiculo`, `factura_articulos` | Manuales, comprobantes y líneas. |
| Mensajería | `notificaciones_usuario`, `mensajes_contacto` | Bandeja del cliente y contacto público. |
| Empresa | `establecimientos`, `auditoria_acciones` | Sedes, mapa y auditoría. |
| Inventario | `articulos`, `articulo_stock_establecimiento`, `articulo_movimientos` | Catálogo, stock por sede y kardex. |
| Control | `schema_migrations` | Registro de migraciones manuales. |

Relaciones principales verificadas:

```text
usuarios 1---n usuarios_vehiculos n---1 vehiculos
vehiculos 1---n codigos_vehiculo
vehiculos n---1 vehiculo_modelos 1---n manuales_modelo
usuarios/vehiculos 1---n mantenimientos
usuarios/vehiculos 1---n facturas_vehiculo 1---n factura_articulos
usuarios 1---n notificaciones_usuario
articulos n---n establecimientos (articulo_stock_establecimiento)
```

LITE no tiene VIN real. Identifica la unidad mediante `codigo_catalogo` y, opcionalmente, placa. Varios vínculos son lógicos y carecen de FK en el esquema legacy.

## 3. Autenticación, sesiones y roles

- Registro público con rol fijo `USUARIO`: `vinova/routes/public_auth.py:351-446`.
- Login por correo, hash Werkzeug, cuenta activa, mensaje anti-enumeración y bloqueo de cinco intentos en memoria: `public_auth.py:98-167`, `core.py:1982-2036`.
- Recuperación mediante token aleatorio, hash SHA-256, expiración y un solo uso: `public_auth.py:170-349`.
- Logout exclusivamente POST: `vinova/routes/logout.py:3-24`.
- Roles cerrados `ADMIN`, `TRABAJADOR`, `USUARIO`; guard central por prefijo/ruta en `core.py:1836-1909`.
- CSRF global para métodos mutables y cabeceras básicas en `core.py:1913-1977`.
- Auditoría de acciones sensibles con actor, IP y user-agent en `core.py:179-210`.

Limitaciones verificadas: el rate limit no es compartido entre procesos; no existe cambio de contraseña con sesión activa; los decoradores `login_required`, `admin_required` y `personal_required` están definidos pero no se usan; no hay scoping por sucursal.

## 4. Portal completo del cliente

`GET /perfil` (`vinova/routes/perfil.py:9-361`) reúne datos del usuario autenticado y renderiza diez secciones en `templates/profile.html`:

1. **Dashboard:** saludo, vehículos, próximo/último servicio, alertas, gráfica de seis meses y actividad reciente.
2. **Mis vehículos:** tarjetas y modal por unidad con resumen, historial, mantenimiento y documentación.
3. **Agregar vehículo:** canje de código privado.
4. **Historial:** servicios no anulados registrados por VINOVA.
5. **Próximos servicios:** fecha/km sugeridos y estado derivado `programado`, `próximo` o `vencido`.
6. **Manuales:** manuales activos del modelo asociado a unidades del cliente.
7. **Facturas:** comprobantes activos, monto, sede y vista protegida.
8. **Perfil:** datos de cuenta, estado y foto.
9. **Notificaciones:** bandeja, contador, leer, marcar todas, ocultar y preferencias.
10. **Configuración:** preferencias visuales sin persistencia y cierre de sesión.

`static/js/script1.js` implementa navegación por hash, búsqueda local de vehículos, vista previa de avatar, modal y pestañas de unidad, y gráfica Chart.js. La mayor parte de los datos se calcula en una sola petición; no es una API de portal.

## 5. Vehículos, propiedad y canje

- Generación criptográfica `VNV-XXXX-XXXX-XXXX`: `core.py:1687-1699`.
- Canje atómico con `BEGIN IMMEDIATE`, validación de código/vehículo, un único propietario, actualización a vendido, auditoría y correo: `routes/perfil.py:982-1174`.
- Generación, desactivación, reactivación, archivo y reversa desde administración/personal: `routes/admin.py:852-1469`, `routes/trabajador.py:539-755`.
- Reversa administrativa guarda snapshot en `canjes_reversados`: `routes/admin.py:1243-1392`.
- Alta/edición de unidad, imagen local validada, modelo 3D GLB/GLTF, estados y catálogo: `routes/admin.py:387-1240`, `core.py:1702-1807`.
- Catálogo público con búsqueda, filtros, rangos, orden whitelist y paginación: `routes/catalogo.py:20-407`.

## 6. Servicios y mantenimiento

`mantenimientos` representa un servicio terminado, no una orden de taller. Personal autorizado busca cliente/unidad (`routes/perfil.py:532-647`), registra tipo, fecha, km, costo, sede y observaciones (`perfil.py:650-906`), y puede anular con motivo (`perfil.py:909-969`).

Las reglas fijas de próxima atención están en `core.py:1235-1327`. El registro crea además una factura y envía correo según preferencias. Los endpoints cliente `/perfil/mantenimiento/registrar` y `/perfil/mantenimiento/<id>/eliminar` son stubs: el cliente no modifica historial.

## 7. Documentos, manuales y facturas

- Manuales por modelo y legacy por vehículo; alta/estado desde `routes/admin.py:2086-2171` y consulta en `perfil.py:188-228`.
- Los manuales se sirven desde `static/docs/manuales` o mediante URL externa (`templates/profile.html:659-700`), sin autorización en la descarga directa.
- Factura manual o generada por mantenimiento, líneas de artículos, PDF y anulación: `routes/facturas.py`, `services/facturas.py`.
- PDFs nuevos en `private/facturas`, normalización anti-traversal y vista con comprobación de propietario/rol: `services/storage.py`, `routes/facturas.py:439-472`.
- WeasyPrint usa `templates/factura_pdf.html`; si falla, se genera un PDF básico (`services/facturas.py:30-240`).

Debilidades que no deben copiarse: montos `REAL`/`float`, impuesto suministrado por formulario, número no secuencial ni único, posible sobrescritura por número repetido, enlace externo de factura sin allowlist y texto tributario que sugiere validez SRI.

## 8. Notificaciones y actividad

- Mensajes manuales de personal con tipo `mensaje`, `alerta`, `mantenimiento` o `factura` y prioridad `normal`, `alta` o `urgente`: `services/notificaciones.py`, `routes/admin.py:1725-1823`, `routes/trabajador.py:319-410`.
- Bandeja del cliente con aislamiento por `usuario_id`, lectura individual/masiva y ocultamiento: `routes/perfil.py:364-459`.
- Preferencias: correo, mantenimiento, alertas, facturas y recordatorios: `perfil.py:462-517`.
- La actividad reciente del dashboard combina mantenimientos y facturas; no existe una tabla de actividad independiente.
- No hay push, chat ni WhatsApp de mensajería. El enlace WhatsApp solo se usa como contacto comercial de artículos.

## 9. Funciones fuera del portal

- Paneles monolíticos ADMIN y TRABAJADOR: vehículos, códigos, usuarios, establecimientos, manuales, mantenimiento, facturación y notificaciones.
- Catálogo público de artículos y disponibilidad por sede, API de gestión, stock, transferencias y movimientos: `routes/articulos.py`.
- Directorio público de establecimientos con mapa y filtros: `routes/instituciones.py`, `templates/instituciones.html`.
- Landing, contacto, catálogo con preview 3D y recursos sociales: `routes/public_auth.py`, `routes/catalogo.py`, `templates/index.html`.
- Validadores de cédula/RUC ecuatorianos, placa, fechas, km, dinero, coordenadas, imágenes, documentos y 3D: `core.py:376-452`, `core.py:917-1327`.

## 10. Integraciones externas verificadas

| Proveedor | Implementación real | Variables | Subida/consulta/reemplazo/eliminación |
|---|---|---|---|
| Cloudinary | Solo avatar: `core.py:157-164`, `routes/perfil.py:1177-1243` | `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | `uploader.upload`, `public_id=vinova/perfiles/usuario_<id>_avatar`, `overwrite=True`, URL transformada 300×300. Reemplaza por el mismo `public_id`; no hay endpoint de borrado ni fallback local. |
| MapTiler + MapLibre 4.7.1 | Mapa público y selector admin: `routes/instituciones.py:31`, `static/js/instituciones.js`, `static/js/admin.js:728-1027` | `MAPTILER_KEY` | Clave pública inyectada al navegador; fallback textual si falta o falla. No almacena archivos. |
| SMTP | `core.py:217-369`; transaccional para registro, reset, canje, mantenimiento y facturas | `EMAIL_MODE`, `SMTP_*`, `CONTACT_EMAIL`, `APP_BASE_URL`, `PASSWORD_RESET_MINUTES` | Modo `simulado` por defecto; SMTP TLS/SSL opcional. |
| WeasyPrint | `services/facturas.py:127-145` | Ninguna | Genera PDF local; fallback propio si no está disponible. |

No se encontraron S3, GCS, R2, Supabase, Firebase ni otro proveedor de archivos en LITE.

## 11. Pruebas y certeza

Solo hay tres pruebas `unittest` de migración de stock (`tests/test_migracion_stock_concesionarias.py`). Las funciones anteriores se verificaron siguiendo ruta, controlador, SQL/servicio y plantilla; una mera plantilla no se contó como implementación.

Incertidumbres que requieren entorno operativo, no más lectura estática:

- Credenciales, cuota y ciclo real de Cloudinary/MapTiler/SMTP no se probaron.
- Los scripts de migración manual y el SQLite pueden divergir entre instalaciones.
- Enlaces externos históricos de manuales/facturas pueden estar caídos o no ser confiables.
- La configuración general del portal muestra toggles visuales que no se persisten; no constituyen funcionalidad real.
