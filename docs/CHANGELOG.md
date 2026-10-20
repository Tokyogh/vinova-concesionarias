# Changelog

Este registro comienza con la línea estable 2.x. Los cambios futuros deben documentarse aquí sin incorporar resultados temporales de QA, manifests ni notas internas de desarrollo.

## Consolidación de seguridad y beta — 2026-10-16

- Sedes públicas enriquecidas y catálogo público de repuestos reutilizando modelos PRO.
- Validación contextual, DNS fijado para webhooks, CSP con nonce y límites de archivos/importaciones/archives.
- Cookies `__Host-`, sesiones revocables, acceso Staff adaptativo y consentimiento previo de tecnologías opcionales.
- Borradores legales/privacidad trazables, pendientes de aprobación jurídica y datos empresariales definitivos.
- Lock Python con hashes, imágenes externas por digest, SBOM y gates de vulnerabilidades/configuración.
- Cobertura documental bilingüe reproducible en código, interfaz y operación.

Estos cambios están verificados localmente y no declaran `PRODUCTION READY` sin los gates externos documentados.

## 2.0.0 — 2026-09-03

- Consolidación estable del flujo comercial, vehículos, inventario, finanzas, reportes y analítica.
- Postventa opcional, notificaciones, campañas e integraciones desacopladas.
- Scopes de sucursal, permisos globales, auditoría, continuidad y recuperación endurecidos.
- Infraestructura Docker, staging, QA aislado y smoke de despliegue consolidados.
- Versión de producto centralizada en `2.0.0`.

## UI Recovery (POST-2.0.0) — v4 Editorial Automotive

- Design System en capas (tokens → base → componentes → layouts → páginas → responsive → a11y → print); tema claro/oscuro nativo, persistente y sin flash.
- Portada editorial: hero `46fr/54fr` texto/fotografía, `hero-frame` reemplazable sin tocar CSS, franja de estadísticas a pie; azul corporativo como acento (nunca fondo pantalla).
- Login split ~50/50 con cover `auth-cover`, formulario `min(440px)` centrado y sin overflow; móvil de una columna.
- Catálogo y solicitudes públicas claras (sin banner navy); perfil público y héroes internos alineados a tokens.
- Artifacts visuales y validación responsive multi-viewport (360–1920 píxeles) sin overflow-x.
