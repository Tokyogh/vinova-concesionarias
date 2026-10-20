# Roadmap de implementación por bloques

Este roadmap empieza después de autorización expresa. Cada bloque debe cerrar con pruebas, informe breve y commit independiente. No se inicia el siguiente si quedan migraciones sin aplicar, tests de aislamiento fallidos o secretos en el diff.

## Orden de dependencias

```text
B0 estabilizar base actual
  -> B1 identidad/autenticación cliente
      -> B2 shell, dashboard y perfil
          -> B3 garaje y detalle de vehículo
              -> B4 servicios e historial
          -> B5 documentos y manuales
          -> B6 facturas y PDF
          -> B7 notificaciones y preferencias
              -> B8 integración transversal y UX
                  -> B9 storage externo y operación
                      -> B10 importación LITE opcional
                          -> B11 cierre integral
```

## B0. Estabilizar la base de garaje existente

**Objetivo.** Convertir los cambios locales de R06 en una base integrada y verificable antes de construir dependencias encima.

**Incluye.** `Customer.account`, `VehicleLinkCode`, `CustomerVehicle`, permisos, generación/revocación/canje/desvinculación/transferencia, UI Staff y pruebas existentes. Corregir GET de canje y reforzar propietario activo único.

**Archivos/módulos.** `apps/accounts/management/commands/seed_roles.py`, `apps/customers/{models,forms,services,selectors,views,urls}.py`, `apps/vehicles/{models,services,selectors,views,urls,internal_urls,admin}.py`, templates internos y `templates/vehicles/redeem.html`.

**Modelos/APIs/migraciones.** Revisar `accounts.0004`, `customers.0003`, `vehicles.0006`; nueva migración solo si se añade constraint parcial de propietario activo. Sin API pública nueva.

**Dependencias.** Ninguna; es el gate de todo el portal.

**Riesgos.** Mezclar cambios del usuario, migraciones aplicadas solo en un entorno, carrera de doble dueño, cuenta vinculada sin permiso.

**Pruebas.** `apps/vehicles/tests/test_garage.py`, customers/accounts, concurrencia en PostgreSQL, migración forward y `migrate --plan`, permisos por sucursal, GET/POST sin `portal.access`.

**Finalización verificable.** Check limpio; migraciones confirmadas; ningún vehículo admite dos dueños activos; cuenta-cliente/rol quedan coherentes; commit exclusivo `portal-base-garage`.

## B1. Identidad cliente, invitación, registro y recuperación

**Objetivo.** Dar acceso autoservicio seguro sin duplicar expedientes ni degradar la seguridad PRO.

**Incluye.** Servicio atómico cuenta↔Customer↔rol cliente, invitación, activación, recuperación de contraseña y registro público opcional configurado por empresa.

**Archivos/módulos.** `apps/accounts/{forms,services,views,urls,models}.py`, `apps/customers/services.py`, `apps/enterprise/{models,forms}.py`, `templates/accounts/`, settings de email.

**Modelos/APIs/migraciones.** Campo `allow_client_registration`; `ClientInvitation` si se adopta invitación persistida. Reutilizar User/Customer/Role. No exponer DRF para registro en este bloque.

**Dependencias.** B0.

**Riesgos.** Enumeración de correos, toma de expediente existente, usuario Staff reutilizado, correo no entregado, tokens repetibles.

**Pruebas.** Rate limit, respuesta anti-enumeración, expiración/un solo uso, conflicto de email/identificación, rol/permiso, rollback atómico y settings registro ON/OFF.

**Finalización verificable.** Un cliente nuevo o invitado entra con `portal.access`; un Customer existente nunca se autoasocia solo por coincidencia; reset funciona sin revelar cuentas; commit `portal-client-auth`.

## B2. Shell, dashboard, perfil y configuración base

**Objetivo.** Crear la experiencia cliente navegable y el punto único de ownership.

**Incluye.** Nueva `apps.portal`, helper `portal_customer_for_user`, layout responsive, dashboard inicial, navegación, avatar, datos de contacto editables, seguridad/2FA/sesiones, estados vacíos y gates de módulos.

**Archivos/módulos.** `apps/portal/{apps,urls,views,selectors,forms}.py`, `config/urls.py`, `apps/accounts/views.py`, `templates/portal/`, `templates/accounts/profile.html`, `templates/base/public.html`, `static/css/ui/portal/`.

**Modelos/APIs/migraciones.** Sin modelo de negocio nuevo. Formulario Customer limita edición a teléfono, WhatsApp, dirección, ciudad/provincia y contacto preferido; identidad y estado son solo lectura.

**Dependencias.** B1.

**Riesgos.** Acceso con Customer inexistente, N+1 en dashboard, romper navegación pública/Staff, exposición de roles internos.

**Pruebas.** 302 anónimo, 403/404 sin portal, Customer A/B, edición permitida/prohibida, queries acotadas, accesibilidad y responsive. Reparar y probar el bloque `title` del perfil.

**Finalización verificable.** Login cliente aterriza en `/mi-cuenta/`; dashboard y configuración cargan sin datos de terceros; staff conserva su dashboard; commit `portal-shell-dashboard-profile`.

## B3. Garaje y detalle privado de vehículo

**Objetivo.** Completar la experiencia de mis vehículos y canje dentro del portal.

**Incluye.** Lista/filtro, tarjeta, detalle privado, multimedia autorizada, datos técnicos, vínculo/fecha/km, canje VNV, estados y empty states.

**Archivos/módulos.** `apps/portal/vehicles.py` o vistas/selectores equivalentes, `apps/vehicles/selectors.py`, `templates/portal/vehicles/`, CSS de vehículos; servicio de canje existente sin duplicarlo.

**Modelos/APIs/migraciones.** Ninguna tras B0. No cambiar status comercial al canjear.

**Dependencias.** B2 y B0.

**Riesgos.** IDOR, mostrar VIN/códigos sensibles, vehículo transferido todavía visible, duplicar detalle público.

**Pruebas.** Cliente solo ve vínculos activos propios, transferencia corta acceso anterior, canje inválido/expirado/usado, multimedia no pública oculta, límite de consultas.

**Finalización verificable.** Paridad de “Mis vehículos”, “Agregar vehículo” y modal/detalle de LITE con ownership PRO; commit `portal-garage-vehicles`.

## B4. Postventa, historial y próximas atenciones

**Objetivo.** Conectar el portal con órdenes reales de postventa y completar datos de recepción/cierre.

**Incluye.** Km recepción/entrega, diagnóstico, cancelación con motivo, recomendación siguiente manual, historial por unidad, citas programadas y vista consolidada.

**Archivos/módulos.** `apps/post_sales/{models,forms,services,selectors,views}.py`, `apps/portal/`, templates Staff de postventa, templates/CSS portal.

**Modelos/APIs/migraciones.** Migración aditiva de ServiceOrder para campos definidos en arquitectura. No crear `Maintenance` paralelo ni tareas periódicas.

**Dependencias.** B3. Debe respetar `VINOVA_MODULE_POST_SALES_ENABLED`.

**Riesgos.** Historial de anterior propietario, cálculo engañoso de próxima atención, módulo OFF, órdenes canceladas mostradas como activas.

**Pruebas.** Aislamiento Customer A/B y transferencia, transiciones, km no decreciente según política, cancelación auditada, módulo ON/OFF, estado visual derivado sin mensajes automáticos.

**Finalización verificable.** Cliente consulta servicios reales y próximas citas/recomendaciones; no existe scheduler, beat ni correo automático de mantenimiento; commit `portal-post-sales-history`.

## B5. Documentos y manuales

**Objetivo.** Entregar biblioteca privada y manuales autorizados sin URLs públicas débiles.

**Incluye.** Listado por tipo/vehículo, detalle, descarga propia, manuales publicados, servicio compartido de streaming, auditoría de descarga y estados expirado/archivado.

**Archivos/módulos.** `apps/documents/{selectors,services,views,models}.py`, `apps/vehicles/models.py` si se necesita asociación de modelo, `apps/portal/`, templates de documentos/manuales.

**Modelos/APIs/migraciones.** Preferir recursos existentes. Solo añadir asociación reutilizable VehicleModel↔VehicleResource si la asociación por VehicleMedia no cubre el caso; no crear `Manual` nuevo.

**Dependencias.** B3 y B2.

**Riesgos.** Path traversal, descarga por URL directa, MIME activo, manual de otro modelo, documento del anterior propietario.

**Pruebas.** 404 ajeno, `no-store`/`nosniff`, archivo faltante, manual publicado/no publicado, transferencia, hash/dedupe y storage sin `.path()` obligatorio.

**Finalización verificable.** Documentos confidenciales solo salen por vista autorizada; manuales propios visibles; ningún enlace `MEDIA_URL` expone privados; commit `portal-documents-manuals`.

## B6. Facturas y PDF privado

**Objetivo.** Mostrar comprobantes empresariales reales y producir artefactos descargables consistentes.

**Incluye.** Listado/detalle de InvoiceRecord, pagos/estado visibles, generación PDF idempotente al emitir, vínculo a PrivateDocument y descarga propia.

**Archivos/módulos.** `apps/invoices/{services,selectors,views}.py`, nuevo `apps/invoices/pdf.py`, `apps/documents/services.py`, `apps/portal/`, plantilla/CSS PDF corporativos.

**Modelos/APIs/migraciones.** Reutilizar `linked_document`; solo migración si se necesita hash/versión/snapshot que no exista. Añadir librería PDF elegida y dependencias de sistema documentadas.

**Dependencias.** B5 y B2. Integración con B4 puede añadirse mediante servicio, no señal frágil.

**Riesgos.** PDF divergente, doble generación, datos tributarios falsos, storage fallido después de emitir, factura de otro cliente.

**Pruebas.** `%PDF`, contenido mínimo, idempotencia, rollback/recuperación, estados, Customer A/B, archivo faltante, número único, montos Decimal.

**Finalización verificable.** Factura emitida genera un único documento privado reproducible y descargable solo por dueño/Staff; sin cambios SRI; commit `portal-invoices-pdf`.

## B7. Notificaciones, contador y preferencias

**Objetivo.** Hacer consumibles por la cuenta cliente las notificaciones ya dirigidas a Customer.

**Incluye.** Bandeja, detalle, contador, leer, marcar todas, archivar, preferencias, y eventos idempotentes de canje/documento/factura/orden.

**Archivos/módulos.** `apps/notifications/{models,selectors,services}.py`, `apps/portal/notifications.py`, navbar público, templates/CSS portal.

**Modelos/APIs/migraciones.** `NotificationPreference` OneToOne Customer. Reutilizar recipient/message/dedup_key.

**Dependencias.** B2 y, para eventos completos, B3-B6.

**Riesgos.** Marcar mensajes ajenos, duplicados por reintento, preferencias ignoradas, campañas exponiendo clientes, correo dentro de transacción.

**Pruebas.** Recipient por user y Customer, Customer A/B, bulk limitado, dedupe, `transaction.on_commit`, preferencias por canal/categoría y cero recordatorios automáticos.

**Finalización verificable.** Cliente recibe y gestiona sus mensajes; contador coincide; eventos permitidos no se duplican; commit `portal-notifications-preferences`.

## B8. Integración transversal, UX y módulos

**Objetivo.** Unir todas las secciones en un portal coherente y robusto.

**Incluye.** Dashboard final, actividad reciente, búsqueda/filtros, paginación, breadcrumbs, accesibilidad, responsive, estados de error/vacío, performance y navegación condicional.

**Archivos/módulos.** `apps/portal/selectors.py`, templates y CSS modular; `apps/common/modules.py`, contexto de navegación y assets.

**Modelos/APIs/migraciones.** Ninguna prevista. Evitar un `ModuleDefinition` si el registro declarativo actual y settings cubren la instalación; ampliar solo con necesidad empresarial aprobada.

**Dependencias.** B3-B7.

**Riesgos.** Dashboard con muchas queries, secciones ocultas solo por CSS, estética inconsistente, accesibilidad deficiente.

**Pruebas.** Query budgets, teclado, WCAG AA, viewport móvil/tablet/escritorio, módulo postventa ON/OFF, URLs directas, snapshot/visual e2e.

**Finalización verificable.** Portal completo, formal y responsive; módulos OFF no aparecen ni son accesibles; CSS por componente/sección; commit `portal-integration-ux`.

## B9. Cloudinary y storage privado externo

**Objetivo.** Llevar a estado operativo las integraciones de almacenamiento sin debilitar privacidad.

**Incluye.** SDK Cloudinary para avatar, env examples, health/smoke; backend S3-compatible privado solo si la empresa lo configura; fallback local documentado.

**Archivos/módulos.** requirements, `config/settings/`, `accounts/storage.py`, `accounts/cloudinary_avatar.py`, `documents/storage.py`, health checks y documentación operativa.

**Modelos/APIs/migraciones.** Ninguna. Migración de objetos se ejecuta como comando separado si se cambia backend.

**Dependencias.** B5-B7 para validar todos los tipos de archivo.

**Riesgos.** Pérdida al reemplazar, URL pública, credenciales filtradas, fallback silencioso en producción, incompatibilidad de `.path()`.

**Pruebas.** Fake SDK unitario, staging real crear/consultar/reemplazar/borrar, S3 save/open/delete, URL firmada, proveedor caído y redacción de secretos.

**Finalización verificable.** Configuración reproducible; ciclo de vida completo verificado; privado sigue privado; commit `portal-storage-integrations`.

## B10. Importación de datos LITE (opcional y separada)

**Objetivo.** Migrar datos históricos solo si se autoriza, sin acoplar despliegue del portal al SQLite.

**Incluye.** Prevalidación, mapeos, hashes, conflictos, dry-run, confirmación, reporte y rollback lógico usando `apps.imports`.

**Archivos/módulos.** Comando/import type nuevo en `apps/imports/`, tests/fixtures sintéticos; nunca escribir en `web_carros/`.

**Modelos/APIs/migraciones.** Ninguna salvo metadata genérica de import si resulta imprescindible. El origen se abre read-only.

**Dependencias.** B0-B9 y decisión explícita de migrar datos.

**Riesgos.** Duplicados, montos float, archivos faltantes, encoding, estados incompatibles, exposición de datos reales en tests/logs.

**Pruebas.** Dry-run, idempotencia, reanudación, conflicto, archivo ausente, rollback, conteos/reconciliación y fixtures anonimizados.

**Finalización verificable.** Dos ejecuciones no duplican; todos los conflictos están reportados; origen intacto; commit `portal-lite-data-import`.

## B11. Cierre y aceptación integral

**Objetivo.** Demostrar paridad útil sin regresiones empresariales.

**Incluye.** Suite completa, seguridad horizontal, e2e por rol, performance, accesibilidad, documentación, backup/restore y checklist de despliegue/rollback.

**Archivos/módulos.** Tests e2e/security/performance, docs operativas y scripts QA existentes. Sin funciones nuevas salvo correcciones de defectos encontrados.

**Modelos/APIs/migraciones.** `makemigrations --check`, `migrate --plan`, backup verificado y restore drill.

**Dependencias.** B0-B9; B10 solo si se autorizó importación.

**Riesgos.** Fallos preexistentes confundidos con regresiones, ambiente distinto a producción, cobertura solo feliz.

**Pruebas.** Cliente A/B, cliente/Staff, cuenta sin Customer, rol expirado, transferencia, módulo OFF, archivos, concurrencia, CSRF, rate limit, e2e móvil y suite empresarial completa.

**Finalización verificable.** Cero fuga horizontal, check/migraciones limpios, criterios de cada bloque demostrados, rollback documentado, SRI intacto y ausencia de recordatorios automáticos; commit `portal-final-validation`.

## Estrategia de commits y recuperación

- Un commit funcional por bloque; migración + modelo + servicio + pruebas del mismo cambio viajan juntos.
- No mezclar refactors generales ni arreglos no relacionados.
- Cada informe de bloque debe registrar commit base, migraciones, pruebas, fallos conocidos y siguiente punto de reanudación.
- Antes de cada bloque: worktree inventariado y backup de DB. Después: `check`, `makemigrations --check`, tests focales y suite proporcional al riesgo.
- Push solo con autorización y remoto/rama confirmados.

## Exclusiones obligatorias

- No convertir en SaaS ni introducir multi-tenancy.
- No modificar `web_carros/`.
- No reintroducir SRI en este flujo.
- No crear recordatorios automáticos de mantenimiento, tareas periódicas ni campañas equivalentes.
- No copiar floats, SQL crudo, guards por prefijo, manuales públicos ni open redirects de LITE.
