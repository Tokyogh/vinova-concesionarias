# VINOVA final asset handoff

Estado N09: **IMPLEMENTED / VERIFIED**. Las nueve fotografías suministradas en `tilin/` fueron identificadas por
contenido, preservadas como originales e integradas como WebP reales bajo `static/img/vinova/`.

| # | Fuente original | Archivo canónico | Uso verificado |
| --- | --- | --- | --- |
| 01 | `Imagen de ChatGPT 7 oct 2026, 20_47_11.png` | `01_dashboard-welcome.webp` | Banner de bienvenida Staff; vehículo a la derecha y overlay/copy en CSS |
| 02 | `Imagen de ChatGPT 7 oct 2026, 20_27_04.png` | `02_hero-home.webp` | Hero Home; copy a la izquierda y vehículo a la derecha |
| 03 | `Imagen de ChatGPT 7 oct 2026, 20_27_40.png` | `03_vehicle-catalog-blue.webp` | Composición editorial azul del hero de catálogo |
| 04 | `Imagen de ChatGPT 7 oct 2026, 20_29_06.png` | `04_vehicle-catalog-silver.webp` | Composición editorial plata del hero de catálogo |
| 05 | `Imagen de ChatGPT 7 oct 2026, 20_33_03.png` | `05_vehicle-catalog-dark.webp` | Composición editorial oscura del hero de catálogo |
| 06 | `Imagen de ChatGPT 7 oct 2026, 20_38_47.png` | `06_workshop-services.webp` | Hero de servicio/postventa |
| 07 | `Imagen de ChatGPT 7 oct 2026, 20_40_26.png` | `07_showroom-about.webp` | Bloque Nosotros/showroom |
| 08 | `Imagen de ChatGPT 7 oct 2026, 20_48_07.png` | `08_contact-location.webp` | Contacto; fotografía de asesoría en showroom |
| 09 | `Imagen de ChatGPT 7 oct 2026, 20_49_00.png` | `09_auth-cover.webp` | Cover premium de login |

## Optimización e integración

- Los canónicos conservan la proporción 16:9 y las dimensiones originales aproximadas de 1670×942; los slots
  verticales usan `object-fit: cover` y `object-position` sin deformación ni reescalado artificial.
- Cada canónico cuenta con variantes WebP de 960 y 640 px, referenciadas mediante `srcset` y `sizes`.
- Peso de los canónicos: 103–253 KB; fuentes PNG preservadas: 1.8–2.3 MB.
- Home, Auth y Dashboard usan carga eager/high por su rol LCP. Showroom, taller, contacto y composición editorial
  usan lazy loading. Todas las imágenes declaran dimensiones intrínsecas para evitar layout shift.
- Las tres fotografías de catálogo son editoriales y decorativas: nunca sustituyen la media real de una unidad.
- El registry allow-listed sólo emite URLs cuando existen el canónico y las variantes disponibles.

## Evidencia

- Registry, WebP y variantes: `apps/common/tests/test_ui_assets.py` — PASS.
- Django/staticfiles y catálogo público dirigido — PASS.
- Chromium Public/Auth + accesibilidad: 17/17 PASS, Light/Dark y viewports 1440×900, 1366×768, 1024×768,
  768×1024 y 390×844.
- Capturas: `private/qa_reports/vinova-next/n09/final/chromium/` y la matriz Public/Auth final con lazy assets
  decodificados en `private/qa_reports/vinova-next/n09/public-final/chromium/`.

No faltan assets obligatorios. La aprobación visual humana continúa separada del cierre técnico.
