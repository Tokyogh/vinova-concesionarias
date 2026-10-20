# Funcionalidades reales

Estado al 2026-10-16. “Implementado” indica código y pruebas locales; no implica
validación de proveedores o staging.

| Dominio | Capacidades | Estado |
|---|---|---|
| cuentas | login email/usuario, logout POST, perfil/avatar, reset, invitación/registro cliente, usuarios y roles | implementado y probado |
| seguridad | política, historial de contraseña, sesiones, 2FA/TOTP, códigos de respaldo, acceso Staff adaptativo y reset administrativo | implementado; 2FA y política Staff no se fuerzan por defecto |
| empresa | perfil, branding, contacto, legales, sitio público y políticas de aprobación | implementado |
| sucursales | CRUD, contacto, horarios, servicios, publicación, coordenadas, foto, website, directorio y mapa | implementado; multimedia real depende del storage configurado |
| clientes | expediente, notas/intereses, identificación, scope y asociación segura a cuenta | implementado |
| portal | dashboard, perfil, preferencias, garaje, documentos, facturas, notificaciones y postventa opcional | implementado y ownership probado |
| vehículos | marcas/modelos, CRUD, publicación, multimedia, specs, recursos, catálogo, favoritos y códigos | implementado |
| inventario | categorías/items, stock por sede, mínimos/ubicación, entradas/salidas/ajustes/transferencias y catálogo público acotado | implementado; catálogo público bajo feature flag |
| CRM/leads | captura pública limitada, pipeline, asignación, actividades, test drive, conversión y export | implementado |
| ventas | cotización, reserva, venta, líneas, pagos, anulaciones, estados y aprobaciones | implementado |
| facturación | comprobante interno, secuencias, líneas, emisión, pagos, anulaciones, PDF y portal | implementado; no es SRI |
| postventa | órdenes, líneas, estados, historial y portal | implementado bajo feature flag OFF por defecto |
| documentos | biblioteca, categorías, privados, manuales, lifecycle y descargas auditadas | implementado |
| notificaciones | bandeja, destinatarios, plantillas, preferencias y campañas | implementado |
| reportes/analítica | reportes operativos, exportaciones y agregados comerciales | implementado |
| imports | plantillas, CSV/XLSX, prevalidación, revalidación y confirmación | implementado; histórico LITE no autorizado |
| privacidad | preferencias de cookies, consentimiento granular, solicitudes, exportación, retención, anonimización y borradores legales | implementado técnicamente; revisión legal pendiente |
| auditoría | eventos, redacción, hash encadenado, filtros, export y alertas | implementado |
| API/integraciones | sesión/bearer, scopes, idempotencia, logs, webhooks HMAC, BI y OpenAPI | implementado local; proveedores/TLS pendientes |
| continuidad | políticas, backups, verificación, restore drills y transfer | implementado; operación real por validar |
| QA | perfiles cerrados, ejecución aislada, resultados y descarga protegida | implementado |
| ayuda | artículos/checklists por rol y ayuda contextual | implementado |
| portal público | inicio, catálogo vehículos/repuestos, instituciones/mapa consentido, legales y captación de leads | implementado; proveedores y revisión visual real pendientes |

## Exclusiones expresas

- integración fiscal SRI operativa;
- recordatorios automáticos de mantenimiento;
- migración/importación histórica desde LITE sin nueva autorización;
- SaaS o multi-tenancy;
- datos persistentes de demostración creados automáticamente.

Inventario detallado: [B1](auditoria-integral/01-inventario-funcional.md).
