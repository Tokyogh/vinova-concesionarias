# ROADMAP ACTIVO

## Estado

Fase actual: integración obligatoria, certificación técnica y ajuste B12 cerrados (B0-B9, B11-B12).
Último bloque validado: B12 — ajustes visuales finales e Instituciones LITE.
Siguiente acción: completar Cloudinary/staging y aprobación visual humana antes de cualquier autorización productiva.
Bloqueos de código: ninguno.
Verificaciones externas pendientes: ciclo Cloudinary real, configuración/smoke del despliegue candidato y aprobación visual humana. PostgreSQL, POSIX y Nginx quedaron validados en Docker aislado.

## Pendientes

- **B10 — Importación histórica LITE.** **OMITIDO POR DECISIÓN PENDIENTE.** No importar datos sin autorización adicional; continuar con B11.
- Ningún bloque obligatorio de implementación pendiente.

## Completados

- **B0:** base Customer/garaje/canje estabilizada; checks y migraciones limpias, `vehicles.0007` aplicada en PostgreSQL, 95 pruebas focales locales y 15 pruebas PostgreSQL superadas (incluida carrera de doble canje).
- **B1:** registro configurable, invitación/activación de un solo uso y recuperación anti-enumeración implementados; 94 pruebas de regresión locales y 7 flujos focales PostgreSQL superados; migraciones `accounts.0005` y `enterprise.0002` aplicadas.
- **B2:** `apps.portal` creado con ownership central, dashboard, perfil, avatar, seguridad y configuración responsive; 38 pruebas focales locales y 27 pruebas PostgreSQL superadas, sin migraciones pendientes.
- **B3:** garaje privado con búsqueda, detalle por vínculo activo, VIN enmascarado, multimedia pública autorizada y canje VNV reutilizado; 27 pruebas locales y 28 PostgreSQL superadas, incluida concurrencia y aislamiento.
- **B4:** historial de posventa aislado por propietario y vehículo activo, ampliación operativa de `ServiceOrder`, cancelación justificada y próxima atención manual; 20 pruebas focales locales y 6 pruebas PostgreSQL superadas, con `post_sales.0002` aplicada y sin recordatorios automáticos.
- **B5:** biblioteca privada con descargas autenticadas y auditadas, separación entre documentos personales y transferibles, y manuales publicados por modelo/año; 30 pruebas locales y 17 PostgreSQL superadas, con `documents.0002` aplicada.
- **B6:** listado y detalle privado de comprobantes, PDF determinista enlazado a `PrivateDocument`, descarga Staff/cliente auditada e idempotencia concurrente; 33 pruebas locales y 30 PostgreSQL superadas, sin integrar SRI ni requerir migraciones.
- **B7:** bandeja privada con contador, lectura, archivo y preferencias; eventos de factura, documento y servicio reutilizan `NotificationMessage`/`NotificationRecipient` con claves idempotentes y aislamiento por `Customer`; migración `notifications.0004` aplicada y concurrencia real validada en PostgreSQL.
- **B8:** dashboard transversal con actividad reciente en una consulta, filtros y paginación persistentes, breadcrumbs, estados vacíos, navegación condicional y presupuesto frío de 32 consultas; 34 pruebas portal locales, 7 focales PostgreSQL y 1 recorrido Chromium en móvil/tablet/escritorio superados, incluido contraste AA y gate directo de postventa OFF.
- **B9:** Cloudinary fijado para avatares y S3-compatible privado conectado con URLs firmadas, cifrado, timeouts y fallback local; readiness consulta proveedores reales, los fallos quedan controlados y existe smoke `check_storage_integrations --live`; 70 pruebas locales relevantes, 39 pruebas focales adicionales y release strict superados, sin migraciones. Los ciclos con credenciales reales quedan explícitamente pendientes en staging.
- **B11:** cierre integral completado; 2.407 pruebas Django aprobadas y 37 omitidas, con el archivo de tres casos de concurrencia que requiere PostgreSQL excluido de esa ejecución; 32/32 E2E Chromium aprobadas sobre once escenarios, Ruff/check/migraciones limpios y restore drill aislado verificado. Informe y gates externos en `06-cierre-integral.md`.
- **Certificación final:** gates ejecutables cerrados; PostgreSQL limpio y seis carreras aprobadas, suite Django 2.418/40, E2E Chromium 32/32, continuidad y release verificados. El veredicto permanece **NO PRODUCTION READY** por pendientes externos. Informe en `07-certificacion-final.md`.
- **B12:** sidebar cliente aligerado, campana SVG, logo privado al hub, hero público sin deformación y directorio `/instituciones/` integrado sobre `Branch` con filtros, mapa MapLibre/MapTiler, fallback seguro y responsive. Informe en `12-ajustes-visuales-e-instituciones.md`; el veredicto permanece **NO PRODUCTION READY**.
