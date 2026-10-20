# 12 — Ajustes visuales finales e Instituciones

Fecha: 2026-10-14  
Rama: `integration/lite-pro`  
Base recibida: `ff8cfea`  
Commit de implementación: `a72ecb8`  
Estado: **implementación local validada; no se declara production-ready**.

## Resumen

Se corrigieron los cuatro hallazgos de la revisión humana sin cambiar la estructura aprobada del portal:

- el sidebar del cliente conserva sus 260 px, jerarquía y distribución, pero usa superficies celestes claras y azules frescos en tema claro; el azul oscuro queda concentrado en el estado activo;
- el rombo usado para notificaciones fue sustituido por una campana SVG coherente en sidebar, topbar y métrica de alertas, con estados normal, hover, focus y no leído;
- la marca `Mi Vinova` enlaza al hub público `/` en escritorio y móvil, mientras `Inicio` continúa llevando al dashboard privado;
- el hero público conserva la composición existente y renderiza la imagen con `object-fit: contain` y alineación derecha, evitando deformación en escritorio, tablet y móvil;
- se incorporó `/instituciones/` con las tres categorías, tarjetas, búsqueda, filtro, listado, mapa, detalle, estados vacíos, responsive y navegación pública de la referencia LITE.

## Referencia LITE auditada

| Área | Referencia de solo lectura | Elementos recuperados en PRO |
|---|---|---|
| Ruta y datos | `web_carros/vinova/routes/instituciones.py`, `web_carros/vinova/core.py:1363-1499` | filtro de tres tipos, conteos, solo registros habilitados, servicios normalizados |
| Interfaz | `web_carros/templates/instituciones.html` | selector superior, workspace, búsqueda, filtro, lista, mapa, panel de detalle, mensajes vacíos |
| Interacción | `web_carros/static/js/instituciones.js` | selección por clic/teclado, búsqueda, filtro, marcadores, encuadre y popup |
| Presentación | `web_carros/static/css/instituciones.css` | cuadrícula de tres columnas, tarjetas por tipo, mapa central, detalle lateral y apilado responsive |
| Recursos | `web_carros/static/img/instituciones/` | tres imágenes de categoría copiadas a `static/img/institutions/`; LITE permaneció sin cambios |

## Integración con arquitectura PRO

No se creó un modelo paralelo de “establecimiento”. `branches.Branch` continúa siendo la fuente única y añade:

- tipo `institution` para instituciones afiliadas;
- provincia, descripción, horario, servicios y coordenadas opcionales;
- validación de latitud/longitud y normalización de servicios;
- propiedades de presentación sin persistir datos duplicados.

El selector público `public_institution_queryset()` expone únicamente sedes con `is_public=True`, `is_active=True`, empresa activa y tipo admitido. Bodegas quedan fuera. Oficinas públicas existentes se presentan como instituciones para mantener compatibilidad; no se reclasifican ni alteran en base de datos.

La administración sigue protegida por `branches.manage`; los nuevos campos se editan mediante el formulario y servicios auditados existentes. El API conserva su permiso global y expone los campos nuevos solo a consumidores ya autorizados. La migración `branches.0003` añade columnas nulas o con valores por defecto y no modifica cuentas, clientes, ownership ni asociaciones existentes.

## Mapa

Se conservó MapLibre GL 4.7.1 + MapTiler, con estas correcciones respecto de LITE:

- clave configurable `MAPTILER_PUBLIC_KEY`, explícitamente pública y restringible por dominio;
- sin script de configuración inline ni secretos de servidor;
- CSP limitada a `unpkg.com` para el recurso versionado y `api.maptiler.com` para datos del mapa;
- el proveedor solo se carga cuando existe clave;
- fallback legible cuando falta la clave, falla el proveedor o no hay coordenadas;
- no se inventan ni reparan coordenadas por coincidencia de ciudad/dirección;
- textos de popup se escapan antes de insertarse.

Las sedes sin coordenadas siguen disponibles en lista y detalle. `seed_demo_organization` prepara de forma idempotente datos demostrativos para las tres categorías; no se ejecuta automáticamente ni altera producción.

## Auditoría comparativa puntual

| Área | Faltaba o divergía | Corrección | Diferencia intencional restante |
|---|---|---|---|
| Sidebar portal | Fondo navy demasiado dominante | Gradiente celeste, texto azul legible y activo corporativo | Tema oscuro conserva una variante oscura por coherencia del modo |
| Dashboard cliente | Glifo rombo en alertas | Campana SVG en todos los puntos de notificación | Datos y controles empresariales PRO permanecen |
| Hub público | Imagen percibida como estirada/cortada | `contain`, proporción intrínseca 1672×941 y fondo suave | Se conserva la composición y contenido PRO |
| Instituciones | Ruta independiente y mapa omitidos | Paridad alta de layout, interacción, datos y responsive | Imagen personalizada por sede no se copia: se usan assets por categoría para no abrir una carga de archivos no auditada |
| Iconografía | Símbolo tipográfico dependiente de fuente | SVG estable, escalable y con estados accesibles | Otros glifos ya aprobados no se rediseñan en este bloque |
| Navegación | Logo privado volvía al dashboard | Logo → hub público; `Inicio` → dashboard | Ninguna |

## Archivos principales

- Dominio y administración: `apps/branches/models.py`, `forms.py`, `selectors.py`, `services.py`, `views.py`, `public_urls.py`, API/admin y migración `0003`.
- Interfaz pública: `templates/branches/public_institutions.html`, `static/css/ui/pages/institutions.css`, `static/js/institutions.js`, `static/img/institutions/`.
- Navegación y seguridad: `templates/base/public.html`, `config/urls.py`, `config/settings/base.py`, `.env.example`, `apps/security_center/middleware.py`.
- Ajustes visuales: `templates/portal/base.html`, `templates/portal/dashboard.html`, CSS del portal y `static/css/ui/pages/home.css`.
- Pruebas: `apps/branches/tests/test_public_institutions.py`, regresión del portal y E2E público/portal.

## Validación

- `python manage.py check`: PASS, 0 issues.
- `python manage.py makemigrations --check --dry-run`: PASS, sin cambios.
- `python manage.py migrate` en PostgreSQL local: `branches.0003` aplicada correctamente, sin borrar o reiniciar datos.
- `python manage.py migrate --check`: PASS.
- Ruff focal: PASS.
- Pruebas focales de directorio/portal/dashboard/seguridad/release y matriz de escalamiento: **920 passed**.
- Suite Django completa final: **2441 passed, 41 skipped**; los skips son escenarios condicionados y E2E separados.
- E2E Chromium `public + portal`: **11 passed**, 0 failed, 0 skipped; búsqueda/filtro/detalle de Instituciones, logo al hub, campanas SVG y hero `contain` cubiertos.
- Matriz visual: 1440×900, 1366×768, 1024×768, 768×1024 y 390×844, temas claro/oscuro, sin overflow horizontal ni controles sin etiqueta.
- Inspección de capturas: sidebar más ligero, hero sin deformación y patrón Instituciones LITE preservado en escritorio/móvil. La automatización visual de Windows no pudo iniciar por recursos ausentes de `@oai/sky`; se usó el runner Playwright reproducible del repositorio.

## Seguridad y compatibilidad

- No cambian `Customer.account`, `portal.access`, roles, ownership, CSRF ni selectors privados.
- El directorio es de solo lectura y no expone sedes privadas, inactivas, bodegas ni empresas inactivas.
- Staff sin autorización no obtiene permisos nuevos.
- `web_carros/` se utilizó solo como referencia y permanece sin modificaciones.
- No se copiaron SQL, credenciales, sesiones ni datos LITE.

## Riesgos y pendientes

- Probar una clave MapTiler restringida y el consumo real del proveedor en staging; el fallback local ya está validado.
- Cargar coordenadas verificadas para sedes reales mediante el panel autorizado.
- Mantener la aprobación visual humana de staging y los demás gates externos documentados en el cierre anterior.
- No hubo merge, despliegue ni cambio de producción; este bloque no autoriza declarar production readiness.
