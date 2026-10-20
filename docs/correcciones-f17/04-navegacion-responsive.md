# F17.9 — Navegación responsive

Fecha: 2026-10-19

## Correcciones

- El encabezado público cambia a drawer hasta 1180 px, antes de que los seis destinos y las acciones de sesión colisionen. El JavaScript y el CSS comparten el mismo breakpoint.
- El portal cliente usa un sidebar persistente en escritorio y un drawer fuera de lienzo hasta 980 px. El estado móvil incluye overlay, bloqueo de scroll, `aria-hidden`, Escape, restauración de foco y sincronización al cambiar el viewport.
- La topbar Staff limita el ancho del nombre y de las acciones; los textos extensos se truncan sin ampliar el documento.
- Los tres shells conservan navegación por teclado, estado activo, controles de tema y acceso a todas sus acciones.

## Viewports comprobados

- Público: 320, 360, 390, 430, 768, 1024, 1366 y 1440 px mediante las matrices existentes y el nuevo caso de drawer tablet.
- Staff: 320, 360, 390, 430 y 768 px; las reglas intermedias cubren 901–1200 px.
- Portal cliente: 390, 768 y 1440 px, incluidas todas sus rutas principales.

## Evidencia Chromium

- Público y accesibilidad: 19 escenarios completaron correctamente sus aserciones; la primera repetición detectó dos expectativas E2E antiguas, no defectos autorizativos.
- La solicitud pública ahora declara `email` como canal preferido cuando el dato sintético solo aporta correo.
- El acceso al logo del portal abre primero el drawer móvil, en vez de enfocar un elemento fuera de lienzo.
- Repetición focal del portal: 1 aprobada, 0 fallos.
- Sin desbordamiento horizontal, errores JavaScript o fallos HTTP inesperados en los recorridos aprobados.
