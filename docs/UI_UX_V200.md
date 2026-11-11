# VINOVA PRO — ROADMAP UI/UX (fuente de verdad visual)

> Fuente de verdad técnica de la interfaz consolidada. El roadmap funcional
> anterior está cerrado; este documento conserva las decisiones vigentes de UI.

## Lenguaje visual — VINOVA CORPORATE AUTOMOTIVE

corporativo · premium · automotriz · amigable · limpio · profesional.

- NO: neon, cyberpunk, RGB, glow, glassmorphism, gradientes chillones, sombras de color, animaciones exageradas, emoji como iconos.
- SÍ: azul corporativo profundo como ACENTO (CTAs, links activos, eyebrow, números), superficies claras/neutras, fotografía automotriz protagonista, bordes limpios, sombras sutiles, tipografía profesional.
- Paleta 100% en tokens (`--primary`, `--primary-2`, `--primary-3`, `--primary-soft`, `--accent`).

## Roadmap

| Fase | Descripcion | Estado |
|------|-------------|--------|
| UI-00 | Frontend architecture assessment | DONE |
| UI-01 | Design System / tokens / themes | DONE |
| UI-02 | Light/Dark functional | DONE |
| UI-03 | Public Home | DONE |
| UI-04 | Authentication | DONE |
| UI-05 | Public Catalog | DONE |
| UI-06 | Vehicle Detail | DONE |
| UI-07 | Services / Post-sales public | DONE |
| UI-08 | About / Corporate | DONE |
| UI-09 | Contact / Branches | DONE |
| UI-10 | Staff shell | DONE |
| UI-11 | Staff modules migration | DONE |
| UI-12 | Responsive global | DONE |
| UI-13 | Accessibility / performance | DONE |
| UI-14 | Frontend architecture cleanup | DONE |
| UI-15 | Final E2E/UI validation | DONE |

## UI-00 Resultado del assessment

- **CSS staff/public**: vinova.css=monolito minificado legacy (68KB, 852 reglas, tokens, capa base NO eliminar).
  design-system.css era monolito de 1199 lineas sobre legacy. Clasificacion: **B** (salvable, requiere modularizacion).
- **JS**: vinova.js vanilla 10KB (toggle+modals+selects) **A**.
- **Python/UI**: vistas+context processor `vinova_product_version` ok **A**.
- **Templates**: herencia base/base.html (staff) y base/public.html (public); login standalone. Duplicacion de links estaticos que se consolido.

## UI-01 Arquitectura CSS (implementada, v4)

```
static/css/
  vinova.css               # Legacy tokenizado. CAPA BASE. NO eliminar.
  ui/
    core.css               # tokens light/dark + base reset + typography (antes secc 1-3)
    components.css         # botones, forms, filtros, cards, tablas, badges, alerts,
                           #   paginacion, modales, theme-toggle, utilidades (secc 4-5+utility)
    layouts.css            # app-shell, sidebar, topbar, header/footer publico (secc 6)
    pages.css              # hero publico, login, catalog, profile, staff, help, detalle (secc 7)
    responsive.css         # breakpoints 1200/1050/1000/900/760/600/480 (secc 8)
    accessibility.css      # focus, reduced-motion, forced-colors, print (secc 9)
```

El split preserva orden de cascada (core→components→layouts→pages→responsive→a11y). Cada base template
carga los 6 modulos tras vinova.css. Sin build step. Reglas nuevas: agregar al archivo UI segun capa.

## Design System (referencia)

- Tokens light/dark en `ui/core.css`. Paleta: primary #0f2f4d / primary-2 #1b5e86 / primary-3 #2b7cb4 /
  accent #c8a24a (dorado premium) / bg #eef1f5 / surface #ffffff / text #16283a.
- Dark: superficies azul-pizarra (#0e1620 bg, #16222f surface, #7fb4e0 primary), accent #d3b576.
- Theme: no-flash inline en `<head>` + toggle `data-theme-toggle` persistente en `localStorage('vinova-theme')`.
  Iconos no contradictorios (moon=light, sun=dark). Estados `*-bg`/`color` token adaptan a dark.
- Overrides dark de heroes legacy en core.css (los existentes en vinova.js/heroes se cubren).

## Composicion (seguimiento del lenguaje, pendiente de foto real)

- Portada: grid `46fr/54fr` (content/media) + franja `public-stats` a pie; fondo claro; unico azul=acento.
  `hero-frame` foto object-fit/cover (reemplazable sin CSS); placeholder silueta automotriz SVG data-uri.
- Login: split `1.06/.94`, cover `auth-cover` (foto reemplazable, overlay en CSS), form `min(440px)` centrado, sin overflow.
- Catalogo/Solicitudes: `catalog-hero` claro (sin banner navy). Detalle: modal (`vehicle_detail_modal`) con galería+tabs.
- Home sections: showroom-about, workshop/services (process-grid), contact/branches (branch-public-grid).
- Staff en design system (dense/compact/neutro). Sidebar navy fijo con theme-toggle.

## Assets pendientes

- Las nueve fotografías definitivas de N09 siguen pendientes por dependencia externa. El registry y los nombres
  canónicos viven en `docs/ui/final-assets-manifest.md` y `static/img/vinova/`; los fallbacks no solicitan archivos
  ausentes. La media de vehículos reales continúa en su biblioteca dinámica y no se sustituye por fotos genéricas.

## Identidad (pulido automotive)

- Hero: placeholder studio con sedán SVG premium (línea + sombra en piso), independiente de tema; chip de texto; foto real swappeable sin CSS.
- Icono unificado de tarjetas/placeholders (sedán con llantas y bujes).
- Favicon "V" SVG data-uri en base/public/login (sin asset pendiente de favicon hasta logo oficial).
- Validado: snapshots 8/8 tras pulido; E2E 10/10; sin overflow.

## Responsive

Breakpoints globales en `ui/responsive.css`: 1200/1050/1000/900(1col shell+hero+login)/760/600(cards+
touch 42px)/480(compacto). Verificado sin overflow en 7 viewports x home/catalog/login/staff.

## Mantenimiento

- NO eliminar vinova.css. NO crear god-file CSS: usar `static/css/ui/` por capa.
- Verificacion rapida tras CSS: brace balance + django check + snapshot home/catalog/login.
- Trivy/gates NO pertenecen a esta iniciativa. Git: commits locales por fase, sin push.
