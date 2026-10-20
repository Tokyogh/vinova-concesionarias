# Reference inventory — web_carros/ (VINOVA original)

> Fase R01 — auditoría exhaustiva de solo lectura.
> Fecha: 2026-10-08. Ruta base: `web_carros/` (referencia protegida, excluida de git).
> Todas las referencias son `archivo:línea` verificadas sobre el código original.
> Números de línea estables mientras `web_carros/` no cambie (no debe cambiar).

---

## 1. Stack tecnológico y estructura

- Framework: **Flask 3.1.3** (sin blueprints: todas las rutas se registran en un único `app` global).
- Persistencia: **SQLite con `sqlite3` crudo, sin ORM** (`vinova/core.py:171` `conectar_db()`, `Row` + `PRAGMA foreign_keys=ON`).
- PDF: **WeasyPrint 69.0** con fallback manual (`requirements.txt`, `vinova/services/facturas.py:127-240`).
- Imágenes de perfil: **Cloudinary** (`vinova/core.py:157-164`).
- Mapas: **MapTiler + MapLibre GL 4.7.1** (`templates/instituciones.html:10,407`, `static/js/instituciones.js:18`).
- Correo: SMTP opcional, **`EMAIL_MODE=simulado` por defecto** (`vinova/core.py:143-154`).
- Sin SQLAlchemy/Alembic/pytest: migraciones artesanales y un único test `unittest`.

### Estructura de directorios

```
app.py                    entry point; importa módulos de rutas (app.py:4-13)
crear_admin.py            consola de creación de ADMIN (crear_admin.py:36)
vinova/core.py (2120)     app, config, helpers, hooks BEFORE/AFTER request (sin rutas)
vinova/routes/            admin(2170) articulos(1372) perfil(1243) trabajador(956)
                          catalogo(503) facturas(472) public_auth(446)
                          instituciones(32) logout(24) errores(6)
vinova/services/          facturas(427) notificaciones(272) storage(250) inventario(129)
templates/ (10)           index, login, reset_password, profile, admin, trabajador,
                          catalog, articulos, instituciones, factura_pdf
static/css (11)           base, styles(landing), styles1(perfil), styles2(login),
                          styles3(catalogo), admin, trabajador, articulos,
                          instituciones, factura_pdf, responsive
static/js (8)             script(landing), script1(perfil), script2(login),
                          script3(catalogo), admin, trabajador, articulos, instituciones
migrations/               runner aplicar_migraciones.py + 6 migraciones registradas
                          + migrar_estructura_vinova.py (manual, sin llamadas)
tests/                    1 archivo: test_migracion_stock_concesionarias.py
docs/                     MODULOS_SERVICIOS.md, FACTURAS_PRIVADAS.md, ACTUALIZAR.txt
private/facturas/         PDFs privados (fuera de static)
```

### Hooks globales de `vinova/core.py`

| Línea | Hook | Función |
|---|---|---|
| 1827 | context_processor | `contexto_csrf` |
| 1835 | before_request | `proteger_rutas_por_rol` (autorización central por prefijo) |
| 1912 | before_request | `validar_csrf_en_post` (CSRF con `secrets.compare_digest`) |
| 1935 | after_request | `inyectar_csrf_en_formularios` (inyección automática) |
| 1971 | after_request | `aplicar_cabeceras_seguridad` (nosniff, X-Frame-Options, Referrer, Permissions-Policy) |
| 2107 | context_processor | `contexto_panel_trabajador` |
| errores.py:3 | errorhandler(413) | archivo demasiado grande |

Decoradores definidos pero **nunca aplicados**: `login_required` (core.py:2065), `admin_required` (2075), `personal_required` (2089).

---

## 2. Rutas / URLs — 68 reglas → 66 endpoints

### public_auth.py (6)
| Método | Ruta | Función | Línea |
|---|---|---|---|
| GET | `/` | `inicio` | 3 |
| POST | `/contacto` | `contacto` | 8 |
| GET+POST | `/login` | `login` | 98 |
| POST | `/recuperar` | `recuperar_password` | 170 |
| GET+POST | `/restablecer/<token>` | `restablecer_password` | 246 |
| POST | `/register` | `register` | 351 |

### logout.py (1)
| POST | `/logout` | `logout` | 3 |

### perfil.py (12)
| Método | Ruta | Función | Línea |
|---|---|---|---|
| GET | `/perfil` | `perfil` (portal cliente, 10 secciones) | 9 |
| POST | `/perfil/notificaciones/<id>/leer` | `marcar_notificacion_leida` | 364 |
| POST | `/perfil/notificaciones/marcar-todas` | `marcar_todas_notificaciones_leidas` | 398 |
| POST | `/perfil/notificaciones/<id>/ocultar` | `ocultar_notificacion_usuario` | 428 |
| POST | `/perfil/notificaciones` | `actualizar_preferencias_notificacion` | 462 |
| POST | `/perfil/mantenimiento/registrar` | stub (solo flash) | 520 |
| POST | `/perfil/mantenimiento/<id>/eliminar` | stub (solo flash) | 526 |
| GET | `/mantenimientos/buscar-vehiculos` | `buscar_vehiculos_mantenimiento` (AJAX) | 532 |
| POST | `/mantenimientos/registrar` | `registrar_mantenimiento_empresarial` | 650 |
| POST | `/mantenimientos/<id>/anular` | `anular_mantenimiento_empresarial` | 909 |
| POST | `/perfil/vehiculo/agregar` | `canjear_codigo_vehiculo` | 982 |
| POST | `/perfil/foto` | `actualizar_foto_perfil` (Cloudinary) | 1177 |

### admin.py (22 reglas / 21 endpoints)
| Método | Ruta | Función | Línea |
|---|---|---|---|
| GET | `/admin` | `admin_inicio` (redirige a `/admin/vehiculos`) | 9 |
| GET | `/admin/vehiculos` | `admin_vehiculos` (renderiza admin.html completo) | 14 |
| POST | `/admin/vehiculos/guardar` + `/vehiculos/guardar` | `admin_guardar_vehiculo` (misma fn, 2 reglas) | 387-388 |
| POST | `/admin/vehiculos/<id>/estado` | `admin_cambiar_estado_vehiculo` | 761 |
| POST | `/admin/vehiculos/<id>/codigo/generar` | `admin_generar_codigo_vehiculo` | 852 |
| POST | `/admin/vehiculos/<id>/archivar` | `admin_archivar_vehiculo` | 977 |
| POST | `/admin/vehiculos/<id>/desarchivar` | `admin_desarchivar_vehiculo` | 1048 |
| POST | `/admin/vehiculos/<id>/eliminar-permanente` | `admin_eliminar_vehiculo_permanente` | 1103 |
| POST | `/admin/canjes/<id>/reversar` | `admin_reversar_canje` | 1243 |
| POST | `/admin/codigos/<id>/desactivar` | `admin_desactivar_codigo_vehiculo` | 1393 |
| POST | `/admin/codigos/<id>/reactivar` | `admin_reactivar_codigo_vehiculo` | 1438 |
| POST | `/admin/usuarios/crear` | `admin_crear_usuario` | 1473 |
| POST | `/admin/usuarios/<id>/rol` | `admin_actualizar_rol_usuario` | 1599 |
| POST | `/admin/usuarios/<id>/estado` | `admin_cambiar_estado_usuario` | 1658 |
| GET | `/admin/notificaciones/buscar-usuarios` | `admin_buscar_usuarios_notificacion` | 1725 |
| POST | `/admin/notificaciones/enviar` | `admin_enviar_notificacion_usuario` | 1749 |
| POST | `/admin/trabajadores/<id>/establecimiento` | `admin_actualizar_establecimiento_trabajador` | 1826 |
| POST | `/admin/establecimientos/guardar` | `admin_guardar_establecimiento` | 1892 |
| POST | `/admin/establecimientos/<id>/estado` | `admin_cambiar_estado_establecimiento` | 2042 |
| POST | `/admin/manuales/guardar` | `admin_guardar_manual_vehiculo` | 2086 |
| POST | `/admin/manuales/<id>/estado` | `admin_cambiar_estado_manual` | 2130 |

### trabajador.py (10)
| Método | Ruta | Función | Línea |
|---|---|---|---|
| GET | `/trabajador` | `trabajador_panel` | 8 |
| GET | `/trabajador/notificaciones/buscar-clientes` | `trabajador_buscar_clientes_notificacion` | 319 |
| POST | `/trabajador/notificaciones/enviar` | `trabajador_enviar_notificacion_usuario` | 343 |
| POST | `/trabajador/vehiculos/<id>/estado` | `trabajador_cambiar_estado_vehiculo` | 422 |
| POST | `/trabajador/vehiculos/<id>/desarchivar` | `trabajador_desarchivar_vehiculo` | 484 |
| POST | `/trabajador/vehiculos/<id>/codigo/generar` | `trabajador_generar_codigo_vehiculo` | 539 |
| POST | `/trabajador/vehiculos/<id>/archivar` | `trabajador_archivar_vehiculo` | 652 |
| POST | `/trabajador/codigos/<id>/reactivar` | `trabajador_reactivar_codigo_vehiculo` | 723 |
| POST | `/trabajador/usuarios/crear` | `trabajador_crear_usuario` (dedupe cédula) | 758 |
| POST | `/trabajador/usuarios/<id>/cedula` | `trabajador_actualizar_cedula_usuario` | 874 |

### articulos.py (11 reglas / 10 endpoints)
| Método | Ruta | Función | Línea |
|---|---|---|---|
| GET | `/articulos` | `catalogo_articulos` (público) | 565 |
| GET | `/articulos/api/gestion` | `articulos_api_gestion` (JSON) | 679 |
| GET | `/articulos/buscar-factura` | `buscar_articulos_factura` (AJAX) | 716 |
| POST | `/articulos/guardar` | `guardar_articulo` | 779 |
| POST | `/articulos/transferir-stock` | `transferir_stock_articulo` | 1036 |
| POST | `/articulos/<id>/estado` | `cambiar_estado_articulo` | 1155 |
| POST | `/articulos/<id>/archivar` | `archivar_articulo` | 1185 |
| POST | `/admin/articulos/<id>/eliminar-permanente` | `eliminar_articulo_permanente` | 1221 |
| GET | `/admin/vehiculos/ocultos/api` + `/inventario/vehiculos/ocultos/api` | `admin_vehiculos_ocultos_api` (2 reglas) | 1289-1290 |
| POST | `/inventario/vehiculos/<id>/activar` | `activar_vehiculo_oculto` | 1323 |

### catalogo.py (2)
| GET | `/catalog` | `catalog` (catálogo público de vehículos) | 163 |
| POST | `/catalog/vehiculos/<id>/preview/guardar` | `catalog_guardar_preview_vehiculo` (personal) | 410 |

### facturas.py (3)
| POST | `/facturas/guardar` | `guardar_factura_vehiculo` | 7 |
| POST | `/admin/facturas/<id>/estado` | `admin_cambiar_estado_factura` (anulación) | 362 |
| GET | `/facturas/<id>/ver` | `ver_factura_vehiculo` (ownership + PDF) | 439 |

### instituciones.py (1)
| GET | `/instituciones` | `instituciones` (directorio público + mapa) | 4 |

Públicas por diseño: `/`, `/catalog`, `/instituciones`, `/login`, `/recuperar`, `/register`, `/contacto`, `/articulos`.
**Brecha**: `/articulos/api/gestion`, `/articulos/buscar-factura` e `/inventario/*` quedan fuera del guard central y dependen de chequeos internos.

---

## 3. Modelo de datos

Sin ORM: SQL crudo. Tablas con DDL en el repo (15) + 4 tablas legacy sin DDL (`usuarios`, `vehiculos`, `usuarios_vehiculos`, `codigos_vehiculo`).

### 3.1 Tablas con DDL

| Tabla | DDL | Columnas clave |
|---|---|---|
| `schema_migrations` | `migrations/aplicar_migraciones.py:83` | version, archivo, tipo, aplicado_en |
| `establecimientos` | `migrations/migrar_establecimientos.py:24-50` | nombre UNIQUE, tipo CHECK(institucion/concesionario/centro_atencion), direccion, ciudad, telefono, servicios JSON, lat, lng, pin_x/pin_y, activo |
| `auditoria_acciones` | `migrations/migrar_auditoria_acciones.py:23-35` | usuario_id/nombre/rol, accion, entidad, entidad_id, detalle, ip, user_agent, creado_en |
| `mensajes_contacto` | `migrar_estructura_vinova.py:170-181` | nombre, correo, telefono, asunto, mensaje, ip, estado='Nuevo' |
| `canjes_reversados` | `migrar_estructura_vinova.py:185-201` | snapshot antes de reversar canje |
| `mantenimientos` | `migrar_estructura_vinova.py:205-233` | usuario_id, vehiculo_id, usuario_vehiculo_id, registrado_por, tipo_servicio, kilometraje_actual, fecha_servicio, intervalo_km/meses, proximo_kilometraje, proxima_fecha, establecimiento, estado='Realizado', costo REAL, anulado/anulado_por/anulado_en/motivo_anulacion |
| `manuales_vehiculo` | `migrar_estructura_vinova.py:269-280` | vehiculo_id, titulo, tipo_documento, archivo, enlace, activo |
| `facturas_vehiculo` | `migrar_estructura_vinova.py:298-317` + columnas generadas `581-596` | usuario_id, vehiculo_id, usuario_vehiculo_id, numero_factura, archivo, fecha_factura, monto REAL, establecimiento, activo, anulado_*; generadas: mantenimiento_id, tipo_factura('Manual'/generada), concepto, subtotal, impuesto, total, hora_factura, generado_por, archivo_pdf, estado='Generada' |
| `vehiculo_modelos` | `migrar_estructura_vinova.py:407-423` | marca, modelo, anio, modelo_3d, preview_sistemas_json (identidad compartida para manuales/3D) |
| `manuales_modelo` | `migrar_estructura_vinova.py:510-521` | modelo_id, titulo, archivo, enlace, activo |
| `notificaciones_usuario` | `migrar_notificaciones_usuario.py:87-101` y runtime `services/notificaciones.py:14-40` | usuario_id (FK CASCADE), remitente_id, tipo(mensaje/alerta/mantenimiento/factura), prioridad(normal/alta/urgente), titulo, mensaje, leida, eliminado_usuario, creado_en, leida_en |
| `articulos` | `migrations/20260705_articulos_inventario.sql:4-32` | codigo_articulo UNIQUE, nombre, categoria, precio/costo/stock/stock_minimo REAL, unidad, estado, activo, unidades_vendidas, archivado_* |
| `articulo_movimientos` | `...sql:34-48` | artículo, tipo_movimiento, cantidad, stock_anterior/nuevo, referencia_tipo/id, creado_por (libro de stock) |
| `factura_articulos` | `...sql:50-64` | factura_id (FK CASCADE), articulo_id, cantidad, precio_unitario, total (líneas de factura) |
| `articulo_stock_establecimiento` | `...sql:66-78` | UNIQUE(articulo_id, establecimiento_id), stock, stock_minimo, unidades_vendidas (stock por sucursal) |

### 3.2 Tablas legacy (sin DDL en repo; esquema inferido desde SQL)

- **`usuarios`**: id, nombre, correo, password (Werkzeug), rol(ADMIN/TRABAJADOR/USUARIO), activo, cedula (sin UNIQUE), establecimiento (texto), foto_perfil (URL Cloudinary), reset_token_hash/expira, 5 flags `notificar_*`, creado_en/actualizado_en. Índice único parcial de correo (best-effort, `migrar_estructura_vinova.py:162`).
- **`vehiculos`**: id, codigo_catalogo (índice único parcial :112), placa, marca, modelo, anio, tipo_vehiculo, combustible, transmision, kilometraje, precio, imagen, modelo_base_id, modelo_3d*, preview_sistemas_json, estado, activo, archivado_*, creado_por/en. **Sin VIN real** (identidad = codigo_catalogo + placa).
- **`usuarios_vehiculos`**: usuario_id, vehiculo_id, codigo_vehiculo_id, kilometraje_inicial, fecha_registro (garaje del cliente).
- **`codigos_vehiculo`**: id, vehiculo_id, codigo, activo, usado, usado_por, fecha_uso, creado_por/en; índices únicos parciales de código y "un código por vehículo" (:123, :133).

### 3.3 Relaciones

```
usuarios 1─n usuarios_vehiculos n─1 vehiculos     (garaje; 1 vehículo = 1 dueño activo)
vehiculos 1─n codigos_vehiculo                    (códigos de canje VNV-XXXX-XXXX-XXXX)
vehiculos n─1 vehiculo_modelos ─n manuales_modelo  (manuales por modelo)
usuarios 1─n mantenimientos n─1 vehiculos ; mantenimientos n─1 usuarios_vehiculos
usuarios 1─n facturas_vehiculo n─1 vehiculos ; facturas_vehiculo 1─n factura_articulos n─1 articulos
articulos 1─n articulo_movimientos ; articulos n─n establecimientos (stock por sucursal)
usuarios 1─n notificaciones_usuario (usuario_id / remitente_id)
usuarios 1─n auditoria_acciones (lógico, sin FK)
establecimientos ← usuarios.establecimiento (texto, NO FK) y articulo_stock_establecimiento.establecimiento_id (FK)
```

### 3.4 Enums / constantes de dominio

- Roles: `ADMIN`, `TRABAJADOR`, `USUARIO`; creables desde panel solo `{USUARIO, TRABAJADOR}` (core.py:132).
- Vehículo `estado`: `Disponible`, `Reservado`, `No disponible`, `Vendido` (admin.py:416-424).
- Artículo `estado`: `Disponible`/`Agotado`. Mantenimiento `estado`: `Realizado`/`Anulado` + estados derivados `programado/proximo/vencido` (core.py:1287-1327).
- Factura `estado`: `Generada`; `tipo_factura`: `Manual` | generada. Notificación `tipo`/`prioridad` (services/notificaciones.py:7-8).
- Extensiones: imágenes `{jpg,jpeg,png,webp}`, documentos `{pdf,jpg,jpeg,png,webp}`, 3D `{glb,gltf}` (core.py:112-114).

---

## 4. Migraciones

Runner manual `migrations/aplicar_migraciones.py` (registro :67-74): establecimientos, artículos SQL, stock concesionarias, auditoría, notificaciones, facturas privadas.
`migrar_estructura_vinova.py` (627 líneas) **no está registrado ni tiene llamadas**: debe ejecutarse manualmente; contiene los CREATE de mantenimientos/manuales/facturas/modelos y los índices únicos parciales.
Auto-sanación en runtime: `services/notificaciones.py:11` (tabla notificaciones) y `routes/articulos.py:216` (filas de stock por sucursal).

---

## 5. Autenticación, roles y permisos

- **Sesión**: cookie firmada Flask, 1 día, `HttpOnly`, `SAMESITE=Lax` (core.py:35-43). Login `public_auth.py:98-167`: consulta parametrizada, `check_password_hash`, rechazo de cuenta inactiva, mensaje genérico (sin enumeración), auditoría con IP/UA (`core.py:179-210`).
- **Rate limit login en memoria**: 5 intentos / 900 s ventana / 900 s bloqueo por clave `ip:correo` (core.py:126-129, 1982-2036; uso `public_auth.py:110-143`). No persiste entre procesos.
- **Recuperación de contraseña**: token `secrets.token_urlsafe(40)` guardado con SHA-256 + expiración 30 min (`public_auth.py:195-211, 246-349`; `core.py:372`). Respuesta única. **No existe cambio de contraseña autenticado**; el perfil es solo lectura (`templates/profile.html:829-873`).
- **Registro público** (`public_auth.py:351-446`): nombre/correo/password ≥ 8, rol fijo `USUARIO`, sin cédula.
- **Autorización central** `core.py:1836-1909` (before_request): `/perfil*` → login; `/admin*` → ADMIN; `/trabajador*` → ADMIN|TRABAJADOR; rutas exactas `/vehiculos/guardar`, `/facturas/guardar`, `/mantenimientos/buscar-vehiculos`, `/mantenimientos/registrar` + prefijos `/mantenimientos/`, `/catalog/vehiculos/` → personal. El resto es público.
- **Protecciones admin**: no crear/asignar/modificar cuentas ADMIN desde panel (admin.py:1483-1485, 1604-1610, 1623-1625, 1683-1685); auto-desactivación prohibida (admin.py:1679).
- **CSRF global** en todo POST con inyección automática (core.py:1912-1968). Cabeceras básicas (core.py:1971-1977). **Sin CSP ni HSTS**.
- Auditoría de acciones sensibles: login, logout, alta de usuarios, cambios de rol/estado, códigos, canjes, facturas, mantenimientos.

---

## 6. Clientes, cédula/RUC y vehículos

### Validación de identificación (ecuatoriana)
- `solo_digitos` core.py:1072 · `validar_cedula_ec` core.py:1077-1109 (10 dígitos, provincia 01-24, tercer dígito <6, módulo 10 vía `calcular_modulo_11` core.py:1112) · `validar_ruc_ec` core.py:1130-1166 (13 dígitos, delega cédula en RUC natural) · `validar_identificacion_ec` core.py:1169 (despacho 10/13).
- Puntos de uso: admin.py:1499, trabajador.py:776 y 885, facturas.py:92, perfil.py:729.
- **Cédula no es clave**: PK `usuarios.id`; dedupe de cédula solo en rutas de trabajador (trabajador.py:784-797, 912-927); **`admin_crear_usuario` NO dedupe** (brecha).
- **Actualización silenciosa de cédula** desde facturación (facturas.py:99) y mantenimiento (perfil.py:736) sin auditoría del valor anterior.

### Búsquedas
- AJAX mantenimientos `perfil.py:532-647`: min 2 chars, LIMIT 30, LIKE sobre correo/nombre/código/marca/modelo/año/código de canje.
- Destinatarios de notificación `services/notificaciones.py:151-217`: min 2, LIMIT ≤25, LIKE incluye cédula.
- Tabla admin usuarios **sin LIMIT** (admin.py:253-272); tabla trabajador LIMIT 80 (trabajador.py:108-126).

### Vehículos
- Alta/edición compartida `admin.py:387-…` (admin y `/vehiculos/guardar`): validaciones marca/modelo/año/km/precio (434-452); bloqueo de "desvender" si tiene registro de usuario (516-522); bloqueo de cambio de `codigo_catalogo` con referencias (524-531).
- Estados: admin.py:761; archivar/desarchivar/eliminar: admin.py:977/1048/1103; versiones trabajador: trabajador.py:422/484/652.
- Fotos locales `guardar_imagen_vehiculo` core.py:1702 con extensión + magic bytes Pillow (core.py:376-452).
- Identidad: `codigo_catalogo` generado `core.py:1772` + `placa` normalizada (core.py:969); **sin campo VIN**.

### Códigos privados de vinculación (canje)
- Generación `generar_codigo_canje` core.py:1687-1699: `VNV-XXXX-XXXX-XXXX`, `secrets.choice`, alfabeto sin ambiguos; generan admin.py:852/926 y trabajador.py:539/601.
- Canje cliente `perfil.py:982-1174`: `BEGIN IMMEDIATE`; valida código activo, no usado, vehículo disponible, no vinculado a otro usuario (1060-1074); inserta `usuarios_vehiculos`, marca código usado, vehículo → `Vendido` + `activo=0`, auditoría y correo.
- Reversa admin `admin.py:1243-1392`: snapshot en `canjes_reversados` (1296), borra vínculo (1331).

### Garaje / portal cliente (`templates/profile.html`, 10 secciones)
- Inicio (`perfil.py:9-75`), mis vehículos, agregar vehículo (canje), historial de mantenimientos (perfil.py:82-138), próximos servicios (perfil.py:156-186), manuales (perfil.py:188-211), facturas (perfil.py:230), perfil, notificaciones (perfil.py:257-262), configuración de preferencias.

---

## 7. Postventa (mantenimientos)

- **Entidad única `mantenimientos`**: NO existe orden de servicio, recepción, citas, ni tabla de diagnóstico/trabajos por orden (grep sin resultados en `vinova/`).
- Reglas de programación: `reglas_mantenimiento` core.py:1243-1266 (aceite 5000 km/6 m; general 10000/12; freno 15000/12; llanta 10000/12; batería 20000/18; fallback 10000/12); `calcular_proximo_mantenimiento` core.py:1269-1284; estados derivados `estado_programacion_mantenimiento` core.py:1287-1327 (programado/próximo/vencido).
- **Registro solo por personal**: `/mantenimientos/registrar` → `perfil.py:650-906`: valida cédula/RUC (725-731), actualiza cédula si cambió (733-742), calcula próximo servicio, INSERT con `estado='Realizado'`, **genera factura automáticamente** (`registrar_factura_generada`, tipo "Mantenimiento", 819-839), auditoría, correo al cliente. El cliente tiene stubs informativos (perfil.py:520-529).
- **Búsqueda de vehículo/cliente para recepción**: `perfil.py:532-647` (correo, nombre, código catálogo, marca/modelo/año, código de canje; calcula km de referencia MAX(mantenimientos)).
- **Anulación**: `perfil.py:909-969` — solo ADMIN o el mismo trabajador que registró (939-941); soft-cancel con motivo; **sin reverso de stock ni anulación automática de la factura**.
- Historiales: trabajador `trabajador.py:140-183` (LIMIT 80, sin filtro por sucursal); admin `admin.py:177` (LIMIT 120); cliente `perfil.py:82-138`.
- Formularios: `templates/trabajador.html:1094-1194` (selector cliente/vehículo, tipo de servicio, km, costo USD, artículos opcionales, descripción).

---

## 8. Facturación, PDF, manuales, artículos, catálogo

### Facturas
- Modelo `facturas_vehiculo` (una tabla para subidas manuales y facturas generadas, discriminadas por `tipo_factura`). Líneas en `factura_articulos`.
- **Numeración**: `generar_numero_factura` core.py:533-535 → `VNV-FAC-YYYYMMDD-<uv_id:05d>-<4 hex>`; **no secuencial, sin UNIQUE, editable por el personal** (trabajador.html:1332) → riesgo de colisión; el nombre de PDF depende del número (`services/facturas.py:47`) por lo que un duplicado sobrescribe el archivo.
- **Cálculo**: con artículos el subtotal se recalcula en servidor desde precios de BD (`routes/facturas.py:116-179`); **sin artículos confía en `monto`/`impuesto`/`descuento` del formulario** (facturas.py:10, 21-22, 180-181). Total = `max(0, subtotal + impuesto - descuento)` (`services/facturas.py:274`).
- **No hay motor de IVA**: `impuesto` es un monto USD tecleado; **cero usos de `Decimal`** en todo el proyecto (montos en REAL/float, formato `"%.2f"`).
- Estados: `estado` siempre `'Generada'`; la anulación real alterna `activo` + motivo (`routes/facturas.py:362-436`) sin tocar `estado`/`anulado` (semántica inconsistente con la migración :608).
- Descarga/consulta: `/facturas/<id>/ver` (`facturas.py:439-472`): login, personal = todas; cliente solo las suyas y `activo=1` (si no → 403/404). Servicio `enviar_factura_pdf_segura` `services/facturas.py:398-427`.
- **Open redirect**: `services/facturas.py:403-404` redirige a `factura["enlace"]` sin lista blanca.

### PDF
- WeasyPrint desde `templates/factura_pdf.html` (A4, 188 líneas) + `static/css/factura_pdf.css` (592 líneas); render en `services/facturas.py:127-145`; **fallback manual** (PDF crudo, latin-1, trunca a 5 ítems) en :148-240.
- Almacenamiento: `private/facturas/<slug>.pdf` (fuera de static); guardia anti-traversal `services/storage.py:47-112`.
- **Branding hardcoded**: bloque `empresa` fijo en `services/facturas.py:120-125`; solo el nombre del establecimiento viene de BD. Pie de página afirma validez tributaria (factura_pdf.html:175-183) sin SRI.

### Manuales
- `manuales_vehiculo` (legacy) y `manuales_modelo` (por modelo compartido, `core.py:682-747`); rutas admin `admin.py:2086/2130`; visibles en perfil (perfil.py:188-211).
- **Descarga vía enlace estático público** `/static/docs/manuales/...` (`profile.html:686,1288`): sin autorización ni comprobación de propiedad.

### Artículos / inventario (`routes/articos.py`, 1372 líneas)
- Catálogo público `/articulos` (565-676) con filtros y disponibilidad por sucursal; API de gestión `/articulos/api/gestion` (679-713); búsqueda para factura (716-776); guardar con SKU automático (779-1035); transferencias de stock (1036-1154); estados/archivo/eliminación (1155-1288).
- Movimientos de stock con `stock_anterior/nuevo` (`_registrar_movimiento_articulo` :264-317) y recálculo derivado (`_recalcular_stock_articulo` :320-344); venta descuenta stock por sucursal desde la ruta de factura (facturas.py:222-290, con fallback silencioso ante `OperationalError`).
- No existe catálogo de servicios separado: "Servicios" es una categoría de artículos.

### Catálogo público de vehículos (`routes/catalogo.py`)
- `/catalog` (163-407): filtros marca/tipo/combustible/transmisión/estado, rangos precio/año/km, texto libre con escape LIKE, orden con lista blanca (10-17), paginación {8,12,16,24}; base `activo=1 AND archivado=0 AND estado IN ('Disponible','Reservado')`.

### Instituciones / sucursales
- Tabla `establecimientos` (con coordenadas lat/lng y `servicios` JSON); página pública `/instituciones` con filtro `?tipo=` (instituciones.py:4-32) y semilla de 3 registros (migrar_establecimientos.py:58-134).
- Alimenta facturas solo con el **nombre** de la sucursal (`services/inventario.py:7-101`, con fallback a la primera concesionaria activa).

---

## 9. Notificaciones

- Tabla `notificaciones_usuario` (creada también en runtime), tipos `mensaje/alerta/mantenimiento/factura`, prioridades `normal/alta/urgente`.
- **Solo envíos manuales del personal**: `admin.py:1749-1823` y `trabajador.py:343-410`; sin eventos automáticos de negocio.
- Operaciones cliente: bandeja en `/perfil` (perfil.py:257-262), marcar leída (364-395), marcar todas (398-425), ocultar (428-459), 5 preferencias (462-517).
- Aislamiento por destinatario (`WHERE usuario_id = session`) verificado en todas las operaciones.
- **Correo aparte**: `enviar_correo` core.py:237-302 (modo simulado por defecto), con puerta de preferencias `usuario_permite_correo` core.py:336-369; eventos: contacto, reset, registro, factura emitida, mantenimiento, canje, alta de usuario.
- Sin WhatsApp, chat ni push.

---

## 10. Integraciones externas (verificadas)

| Proveedor | Uso | Referencia | Claves `.env` (solo nombres) |
|---|---|---|---|
| **Cloudinary** | exclusivamente avatares | `core.py:157-164` config; subida única `perfil.py:1197-1204` (`public_id=usuario_<id>_avatar`, overwrite, recorte 300×300); sin fallback local | `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` |
| **MapTiler + MapLibre GL 4.7.1** | mapa público de instituciones y selector admin | `instituciones.py:31`, `admin.py:383`, key en HTML `instituciones.html:404`, style `api.maptiler.com/maps/dataviz-dark/style.json` (`instituciones.js:18`, `admin.js:760`) | `MAPTILER_KEY` (expuesta al navegador por diseño) |
| **SMTP** | correo transaccional | `core.py:237-302`; `EMAIL_MODE=simulado` por defecto (imprime en consola) | `EMAIL_MODE`, `SMTP_HOST/PORT/TLS/SSL/USER/PASSWORD`, `SMTP_FROM_*`, `CONTACT_EMAIL`, `PASSWORD_RESET_MINUTES` |
| **WeasyPrint** | generación de PDF | `services/facturas.py:127-145` | — |

No existen: S3/boto3, Supabase, Firebase, imgbb, Drive, Leaflet, Google Maps JS. Sin claves hardcodeadas en código (barrido verificado).

---

## 11. Templates, JavaScript y CSS

### Templates (10) y quién los renderiza
| Template | Propósito | Ruta |
|---|---|---|
| `index.html` | landing pública con hero + preview 3D | GET `/` (public_auth.py:3) |
| `login.html` | login + modales registro/recuperación/soporte/contacto/nosotros | GET `/login` |
| `reset_password.html` | formulario de reset por token | `/restablecer/<token>` |
| `catalog.html` (57 KB) | catálogo público de vehículos | `/catalog` (catalogo.py:380) |
| `instituciones.html` | directorio + mapa MapTiler | `/instituciones` |
| `profile.html` | portal cliente (10 secciones) | `/perfil` |
| `trabajador.html` (1509 líneas) | panel staff (11 secciones) | `/trabajador` |
| `admin.html` (3028 líneas) | panel admin (16 secciones, ids `admin-*` en :220-2938) | `/admin/vehiculos` |
| `articulos.html` | catálogo público de repuestos | `/articulos` |
| `factura_pdf.html` | layout A4 para WeasyPrint | render interno `services/facturas.py:133` |

### JavaScript (8 archivos)
| Archivo | Funciones principales |
|---|---|
| `script.js` (310) | landing: iconos Lucide, modal 3D, tabs, sistemas |
| `script1.js` (309) | perfil: secciones/hash, avatar con validación cliente (≤25 MB), campana, búsqueda interna, autofill km, Chart.js |
| `script2.js` (362) | login: modales, visibilidad contraseña, tema |
| `script3.js` (1078) | catálogo: filtros/rangos, favoritos, paginación, preview 3D editable, formato numérico |
| `admin.js` (1064) | router de secciones, filtro de listas, búsqueda AJAX de vehículos/destinatarios, constructor de líneas de factura, **selector de coordenadas MapTiler** (:727-1027), guardas de doble envío |
| `trabajador.js` (576) | router, búsqueda interna, confirmaciones, generador de códigos, destinatarios |
| `articulos.js` (820) | paneles de artículos vía API JSON, stock por sucursal, builder de facturas (`updateTotals` :588), catálogo público, helper CSRF `vinovaGetCsrf` (:41) |
| `instituciones.js` (508) | mapa, marcadores, filtros, fallback sin key |

### CSS (11)
`base.css` (tokens `--vinova-*`), `styles.css` (landing), `styles1.css` (perfil), `styles2.css` (login), `styles3.css` (catálogo), `admin.css` (incl. picker MapTiler), `trabajador.css`, `articulos.css`, `instituciones.css`, `factura_pdf.css`, `responsive.css`.

---

## 12. Filtros y validaciones

### Servidor
- Cédula/RUC: ver §6. Fechas: `normalizar_fecha` core.py:1181 (YYYY-MM-DD), visual `formatear_fecha_visible` :1198 (DD/MM/YYYY).
- Dinero: `normalizar_precio` core.py:984-1045 → **float**, con ambigüedad de separadores (`"28.900"` → 28900). KM: `normalizar_kilometraje` :924. Placa: :969. Coordenadas: `normalizar_coordenada` :1048 (-90/90, -180/180).
- Imágenes/documentos: extensión + Pillow/magic bytes (core.py:376-452).
- Filtros de consulta: catálogo (`q`, marca, tipo, combustible, transmisión, estado, rangos precio/año/km, orden whitelist, paginación whitelist — catalogo.py:20-300); artículos (`q`, categoría, marca, orden, paginación — articulos.py:569-574); instituciones (`?tipo=`); destinatarios (min 2 chars, LIMIT ≤25); mantenimientos (min 2, LIMIT 30).
- **Sin filtros por rango de fechas.**

### Cliente
- `required` masivos, `minlength=8` en contraseñas, `maxlength=13` en cédula/RUC, `maxlength=16` en placa, rangos numéricos (año 1980-2035, km ≥0, dinero step 0.01), `inputmode=numeric|decimal`; sin `pattern=`.
- JS: validación de avatar (tipo + 25 MB), clamping de rangos, `confirm()` en acciones destructivas, guardas de doble envío.

---

## 13. Seguridad — qué conservar y qué NO copiar

### Conservar (buenas prácticas del original)
1. Autorización en backend, central y por prefijo (core.py:1836-1909) — nunca confiar en la UI.
2. CSRF global con comparación constante-tiempo e inyección automática.
3. SQL parametrizado en todas las consultas revisadas; escape de LIKE.
4. Mensajes genéricos anti-enumeración en login y recuperación.
5. Rate limit de login (aunque hay que persistirlo).
6. Reset de contraseña por token aleatorio hasheado + expiración + un solo uso.
7. Documentos privados fuera de `static` con verificación de propiedad y guardia de path traversal.
8. Validación real de imágenes con Pillow + magic bytes.
9. Transacciones `BEGIN IMMEDIATE` en canjes y ventas con artículos.
10. Auditoría con IP/user-agent en acciones sensibles.
11. Códigos de vinculación aleatorios (`secrets`), revocables, con snapshot de reversa.
12. Aislamiento de notificaciones/facturas/garaje por `session["usuario_id"]`.

### NO copiar (debilidades detectadas)
| # | Hallazgo | Referencia |
|---|---|---|
| S1 | Decoradores de rol definidos y sin usar; protección dependiente de prefijos | core.py:2065-2104 vs 1836-1909 |
| S2 | Rate limit en memoria (no multi-proceso, se pierde al reiniciar) | core.py:126-129 |
| S3 | `TRUST_PROXY_HEADERS` acepta X-Forwarded-For sin validación de proxy | core.py:130, 1982-1989 |
| S4 | Sin cambio de contraseña autenticado; modo de correo simulado por defecto | ausencia de ruta; core.py:143 |
| S5 | **Sin scoping por sucursal**: todo el personal ve toda la instalación | admin.py:253-272, trabajador.py:108-126 |
| S6 | Listados sin paginación/LIMIT (usuarios admin) | admin.py:253-272 |
| S7 | `admin_crear_usuario` no deduplica cédula | admin.py:1473-1539 |
| S8 | Cédula actualizada en silencio desde factura/mantenimiento sin auditoría | facturas.py:99, perfil.py:736 |
| S9 | Helper `usuario_es_ultimo_admin_activo` nunca invocado | core.py:2039-2060 |
| S10 | Sin CSP ni HSTS | core.py:1971-1977 |
| S11 | Sin `session.clear()` previo en login | public_auth.py:145-149 |
| S12 | Clave MapTiler en HTML público (restringir por dominio) | instituciones.html:404 |
| S13 | Cloudinary sin fallback local en error | perfil.py:1217-1220 |
| S14 | Totales confiados al cliente en facturas sin artículos | routes/facturas.py:180-181 |
| S15 | Montos en float/REAL, sin Decimal; sin motor de IVA | global (0 usos de Decimal) |
| S16 | Numeración de factura no única/secuencial; colisión = sobrescritura de PDF | core.py:533-535, services/facturas.py:47 |
| S17 | Manuales servidos como estáticos públicos sin autorización | profile.html:686,1288 |
| S18 | Open redirect vía `factura["enlace"]` | services/facturas.py:403-404 |
| S19 | Anulación de factura inconsistente (`estado`/`anulado` sin tocar; sin reverso de stock) | routes/facturas.py:362-436 |
| S20 | Fallback de concesionaria puede etiquetar la sucursal equivocada | services/inventario.py:89-99 |
| S21 | Pie del PDF afirma validez tributaria sin SRI | factura_pdf.html:179 |
| S22 | `/articulos*` e `/inventario/*` fuera del guard central | core.py:1836-1909 |

---

## 14. Tests, docs y artefactos

- `tests/test_migracion_stock_concesionarias.py` (113 líneas, `unittest`, 3 tests de migración de stock). Sin pytest/CI en el original.
- `docs/MODULOS_SERVICIOS.md` (regla routes→services), `docs/FACTURAS_PRIVADAS.md` (PDF fuera de static), `docs/ACTUALIZAR.txt` (workflow git; nota obsoleta `flask --app app migrar-db`).
- Artefactos no tocados: `vinova.db` + 2 backups, `private/facturas/*.pdf` (2), `static/docs/manuales/*.pdf` (2).
- Repo anidado `web_carros/.git` (rama `main`, worktree `agents/buscar-bug-ue`) — no commitear ni modificar.

---

## Ámbitos de R01 y estado de cobertura

| Bloque | Estado |
|---|---|
| 1. Estructura, rutas, URLs | AUDITADO (§1-2) |
| 2. Modelos y relaciones | AUDITADO (§3-4) |
| 3. Autenticación, roles, permisos | AUDITADO (§5) |
| 4. Clientes, cédula/RUC, vehículos | AUDITADO (§6) |
| 5. Postventa y mantenimientos | AUDITADO (§7) |
| 6. Facturas, manuales, PDF | AUDITADO (§8) |
| 7. Notificaciones, mapas, storage externo | AUDITADO (§9-10) |
| 8. Templates, JS, filtros, validaciones | AUDITADO (§11-12) |
| Seguridad y casos especiales | AUDITADO (§13) |

