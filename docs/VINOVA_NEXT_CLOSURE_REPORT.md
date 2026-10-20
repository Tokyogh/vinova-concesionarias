# VINOVA NEXT — Informe de cierre técnico

Estado: **TECHNICAL UI PASS / N09 Y N16 COMPLETADAS**

Fecha: 2026-10-07

Rama: `feature/v0-2-auth-roles`

HEAD base de las correcciones post-N16: `fcedcff1e61df09486a73996280fe6606575184d`

Este informe cierra técnicamente VINOVA NEXT N00–N16. No equivale a aprobación visual humana ni autorización de
push: `VISUAL_APPROVED: NO`, `FINAL_HUMAN_REVIEW: PENDING` y `PUSH_AUTHORIZED: NO` se mantienen.

## Resultado técnico

- N00–N16 están completos y la roadmap consumible no conserva fases pendientes.
- Dashboard, Staff shell, controles, filtros, favoritos/recientes, Ctrl+K, Assist y búsqueda universal mantienen
  autorización backend y scope de sucursal/ownership.
- Lifecycle, backup/transfer, manifest firmado, preflight y Update Center conservan la separación entre Django y el
  componente privilegiado de despliegue.
- Las nueve fotografías definitivas de N09 están optimizadas, registradas e integradas sin alterar lógica de negocio.
- No se detectaron regresiones CRITICAL, HIGH o MEDIUM introducidas por VINOVA NEXT.

## Integración final de assets N09

- Nueve canónicos WebP reales en `static/img/vinova/`, con 18 variantes responsive de 640/960 px.
- Canónicos entre 103 y 253 KB; originales PNG entre 1.8 y 2.3 MB preservados en `tilin/`.
- `srcset`, `sizes`, dimensiones intrínsecas, prioridad LCP y lazy loading aplicados según el slot.
- Home, catálogo editorial, servicios, Nosotros, contacto, login y Dashboard usan sus fotografías definitivas.
- El catálogo conserva la media real de cada unidad; los tres assets generados sólo forman una composición editorial.
- La fotografía de contacto corresponde visualmente a asesoría en showroom y conserva el nombre canónico compatible
  `08_contact-location.webp`.

El mapeo fuente → destino y la política de crops están documentados en `docs/ui/final-assets-manifest.md`.

## Regresión final

La regresión integral N15 permanece válida: 9/9 gates, 2181 pytest y Chromium 29/29 PASS sobre PostgreSQL/Redis
aislados, sin warnings ni regresiones críticas/altas/medias.

Validación posterior a la integración N09:

| Gate | Resultado |
| --- | --- |
| Django system check | PASS · 0 issues |
| Registry, decodificación WebP y variantes | PASS |
| Tests dirigidos de assets + catálogo | 5/5 PASS |
| Chromium Public/Auth + accesibilidad | 17/17 PASS |
| Viewports | 1440×900 · 1366×768 · 1024×768 · 768×1024 · 390×844 |
| Temas | Light/Dark PASS |
| Imágenes / consola / controles / overflow | Sin 404, errores, controles sin nombre ni overflow horizontal |

Evidencia privada de N09: `private/qa_reports/vinova-next/n09/final/` para la regresión combinada y Dashboard, y
`private/qa_reports/vinova-next/n09/public-final/` para la matriz Public/Auth final con lazy assets decodificados.
Incluye cinco rutas, cinco viewports y ambos temas. Los reportes privados no se versionan.

## Estado de cierre N16

- Arquitectura, lifecycle y documentación coinciden con la implementación verificada.
- Git fue revisado; `tilin/` permanece sin modificar y fuera del staging final.
- No hay assets externos pendientes ni findings nuevos de seguridad abiertos.
- La única acción pendiente es la revisión visual humana opcional y una futura instrucción expresa de push.

Los findings históricos LOW/INFO de D10 continúan documentados en `docs/VINOVA_PRO_FINAL_REPORT.md`.

## Correcciones visuales post-N16

Estado: **IMPLEMENTED / VERIFIED**. Estas correcciones no reabren N09/N16 ni alteran permisos o lógica de negocio.

| Corrección | Causa verificada | Resolución |
| --- | --- | --- |
| Navegación pública activa | Servicios y Nosotros eran fragmentos de Home; el servidor no podía distinguirlos al recargar. La selección restante dependía de subcadenas de URL. | Rutas públicas reales `/servicios/` y `/nosotros/` reutilizan el Home, conservan sus anclas y determinan `aria-current="page"` mediante `resolver_match`. Vehículos y Contacto usan su namespace, incluidas rutas secundarias. Home no marca ninguna sección. |
| Empalme del hero en Dark | El overlay usaba `#0b1f3a`, distinto de la superficie dark semántica. | El degradado desktop/tablet parte de `var(--surface)` y se disuelve con `color-mix`, sin banda ni corte visible. |
| Acciones rápidas numeradas | El template renderizaba el índice del bucle como icono. | Nueve SVG inline semánticos, monocromáticos y coherentes con el sistema visual sustituyen los números sin dependencias externas. |
| Marcas como navegación | La marca pública ya enlazaba a Home, pero faltaba foco visual reforzado; la marca Staff desktop no era enlace. | La marca pública conserva Home con hover/focus; la marca interna enlaza al router autorizado `/dashboard/` y funciona con teclado. |

### Verificación post-N16

- Django check: PASS, 0 issues.
- Registry/formatos/rutas dirigidas: 17/17 pytest PASS; Ruff PASS.
- Chromium dirigido: 22/22 PASS después de corregir una aserción de prueba para navegación oculta en móvil.
- Matriz Public/Auth: Home, catálogo, detalle, Servicios, Nosotros, Contacto y Login; 1440×900, 1366×768,
  1024×768, 768×1024 y 390×844; Light/Dark; 70 capturas.
- Matriz Dashboard: los mismos cinco viewports y ambos temas; 10 capturas.
- Sin overflow horizontal, imágenes rotas, errores de consola ni controles sin nombre; enlaces de marca y estado activo
  verificados también mediante teclado.
- Evidencia privada: `private/qa_reports/vinova-next/post-n16-public-rerun/` (matriz Public/Auth final) y
  `private/qa_reports/vinova-next/post-n16-visual-corrections/` (Dashboard y regresión Staff/accesibilidad).

### Revalidación física de N09

Los nueve canónicos y sus 18 variantes se abrieron físicamente con Pillow: 27/27 reportan formato `WEBP`, modo RGB
y dimensiones proporcionales. `findstatic` resolvió cada canónico desde `static/img/vinova/`. No existen referencias
de ejecución a `tilin/`, rutas absolutas Windows ni duplicados funcionales; los originales permanecen intactos y fuera
del staging.

Se mantienen `TECHNICAL_UI_STATUS: PASS`, `VISUAL_APPROVED: NO`, `FINAL_HUMAN_REVIEW: PENDING` y
`PUSH_AUTHORIZED: NO`.

## Marca Staff y respaldo local `tilin/`

Estado: **IMPLEMENTED / VERIFIED**.

- La regla genérica `.sidebar .brand-block span` anulaba el `display: grid` del icono por mayor especificidad y
  desalineaba el icono respecto del copy. Los selectores ahora se limitan a `.sidebar-brand-copy`; el enlace usa una
  fila flex estable, el icono conserva 40×40 y el texto evita saltos de línea.
- El conjunto icono + nombre enlaza mediante `{% url 'dashboard:home' %}` al index público `/`. Un usuario Staff
  autenticado puede abrirlo sin redirección al panel ni pérdida de sesión, y conserva “Panel interno” para regresar al
  router autorizado del dashboard.
- Los 27 WebP de `static/img/vinova/` están versionados: nueve canónicos y 18 variantes responsive. No hay uso directo
  de `tilin/` ni dependencia funcional de sus PNG; `collectstatic` resuelve los assets canónicos.
- `tilin/` permanece intacto como respaldo local temporal y está oculto únicamente mediante `.git/info/exclude`, que
  no se versiona. Es prescindible sólo después de que el propietario autorice expresamente su eliminación.
- Evidencia privada Light/Dark desktop/móvil: `private/qa_reports/vinova-next/staff-brand-home-link/`.

## Geometría definitiva de la fotografía del Hero Home

Estado: **IMPLEMENTED / TECHNICALLY VERIFIED / HUMAN REVIEW PENDING**.

- La estructura de `c093d3c` conservaba un wrapper `.hero-stage` y permitía que el breakpoint cambiara `.hero-media`
  de absoluta a relativa. Aunque la matriz local de escritorio no reprodujo el desplazamiento reportado, esa segunda
  caja de layout dejaba la geometría innecesariamente expuesta a reglas responsive y cascada heredada.
- `.public-hero` es ahora el único contenedor geométrico. En escritorio, `.hero-media` y `.hero-image` usan
  `position: absolute`, `inset: 0`, ancho/alto 100%, sin ratio, margen, transform ni máximo heredados. La franja de
  beneficios quedó fuera del hero para que la foto coincida exactamente con su alto y borde superior.
- El difuminado se aplica directamente a `.hero-image` mediante `mask-image` y `-webkit-mask-image`: la fotografía es
  transparente hasta 20%, progresa ampliamente entre 35–80% y alcanza opacidad completa desde 85%. Ya no existe
  `.hero-photo-veil` ni un degradado de color usado como sustituto de la transparencia.
- Dark reduce moderadamente brillo y saturación de la imagen sin blur; Light mezcla la transparencia con la superficie
  clara. Ambos conservan el vehículo nítido y visible en la mitad derecha.
- `sizes="100vw"` hace que escritorio use una fuente adecuada al ancho real, evitando ampliar la variante de 960 px.
- A 900 px o menos el apilado es intencional y explícito; la imagen recibe una máscara vertical propia y no altera las
  reglas invariantes de 1024, 1366 o 1440 px.
- La fotografía original, navbar, logotipo, botones, dashboard, permisos y lógica de negocio no cambiaron.
- La matriz Playwright Public/Auth dirigida pasó en 1440×900, 1366×768, 1024×768, 768×1024 y 390×844,
  Light/Dark. Las aserciones verifican rectángulos de hero, media, imagen, titular y botones; coincidencia de bordes y
  alturas en escritorio; máscara computada distinta de `none`; carga real de la imagen; y ausencia de overflow,
  errores de consola, imágenes rotas o controles sin nombre.
- La inspección visual confirma foto al borde superior, texto y vehículo coexistiendo horizontalmente, lado derecho
  cubierto, transición progresiva sin costura y apilado controlado en 768/390 px.
- Evidencia final: `private/qa_reports/vinova-next/hero-photo-geometry-final/`; matriz completa en
  `private/qa_reports/vinova-next/hero-photo-geometry-final-full/` y evidencia E2E en
  `private/qa_reports/vinova-next/hero-photo-geometry-e2e/`.

Se mantienen `VISUAL_APPROVED: NO`, `FINAL_HUMAN_REVIEW: PENDING` y `PUSH_AUTHORIZED: NO`.

## Preparación segura de la copia comercial

Revisión ejecutada el 19 de octubre de 2026, limitada a los ocho hallazgos `generic-api-key`
reportados en cinco pruebas de seguridad y a la comprobación de `nd.txt`.

- Los ocho hallazgos correspondían a un único valor sintético repetido y usado exclusivamente
  dentro de pruebas; no se identificó una credencial real en esas ubicaciones.
- Los fixtures autenticados mediante `force_login` ahora crean usuarios sin contraseña utilizable.
- Los dos flujos que ejercitan login generan una credencial efímera durante cada prueba y la
  reutilizan solo en memoria.
- No se añadieron exclusiones, allowlists ni supresiones de Gitleaks, y no se eliminó ninguna prueba.
- Verificación afectada: `907 passed, 1 skipped`.
- Gitleaks 8.30.1 sobre toda la copia comercial: cero hallazgos.
- `nd.txt` no está presente en la copia comercial. Las credenciales que hayan aparecido en el
  archivo histórico del repositorio original deben rotarse antes de cualquier publicación.
- No se inicializó Git ni se realizó push, merge o despliegue.

Estado: el árbol comercial queda preparado para el siguiente paso controlado, pero la publicación
permanece condicionada a confirmar la rotación de las credenciales históricas y a las aprobaciones
de cierre ya pendientes.
