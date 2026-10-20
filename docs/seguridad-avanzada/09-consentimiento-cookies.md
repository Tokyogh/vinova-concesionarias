# F9 — Consentimiento de cookies y tecnologías similares

Fecha: 2026-10-16

## Alcance e inventario verificado

VINOVA PRO distingue tecnologías necesarias de tres categorías opcionales. Ninguna casilla opcional aparece premarcada y aceptar, rechazar o configurar tienen acceso equivalente desde el primer aviso.

| Categoría | Tecnología | Finalidad | Estado antes de decidir |
|---|---|---|---|
| necesaria | cookie de sesión Django | autenticación, seguridad y continuidad de la sesión | disponible cuando el flujo la necesita |
| necesaria | cookie CSRF Django | protección de formularios y peticiones mutables | disponible cuando el flujo la necesita |
| necesaria | cookie firmada de preferencias | versión, fecha y categorías de la elección | se crea solo al decidir |
| preferencias | `localStorage` de tema, favoritos, vistas y navegación | recordar ajustes del navegador | apagado y purgado |
| analítica | `VehicleInteraction` de primera parte | medir vistas y acciones del catálogo con identificadores hash | apagado; no crea evento ni sesión |
| contenido externo | MapLibre desde unpkg y mapas MapTiler | mapa interactivo de establecimientos | no carga scripts, CSS, estilo ni clave pública |

Los enlaces a Google Maps se abren solo por acción expresa del usuario y no precargan recursos. Cloudinary, si se configura como almacenamiento de activos funcionales, y Sentry en el servidor requieren clasificación contractual/legal por despliegue; este control no los presenta como analítica del navegador ni inventa una base jurídica.

## Implementación

- La elección se almacena en una cookie firmada, `HttpOnly`, `SameSite=Lax`, con ruta `/`, versión del aviso y fecha ISO. En producción usa el prefijo `__Host-` y `Secure`.
- Una firma inválida, una versión anterior o la expiración vuelven al estado sin decidir; no habilitan categorías por defecto.
- El servidor bloquea analítica y recursos de mapa antes de renderizarlos. JavaScript aplica una segunda barrera para preferencias locales y mapa.
- La lista de instituciones, datos de contacto y filtros siguen disponibles si se rechaza el mapa externo.
- El panel de preferencias permite cambiar o retirar la elección en cualquier momento desde interfaces públicas, Staff, portal y login.
- El flujo usa formularios POST con CSRF y valida el destino de retorno para evitar redirecciones abiertas. No depende de JavaScript para guardar la decisión.

## Privacidad y minimización

La evidencia técnica contiene solo versión, fecha y tres booleanos. No contiene correo, nombre, IP, cuenta ni identificador publicitario. Los eventos del catálogo existentes continúan usando hashes; ahora solo se crean tras aceptar analítica. El consentimiento de cookies no sustituye el consentimiento o fundamento aplicable a leads, contratos, comunicaciones o tratamiento empresarial.

## Evidencia automatizada

- Aceptar todo, rechazar y selección granular generan una preferencia firmada válida.
- Firma manipulada y versión obsoleta no conceden categorías.
- Se impiden redirecciones externas desde el retorno del formulario.
- Sin consentimiento no se crea `VehicleInteraction` ni cookie de sesión por una vista de ficha.
- La clave, CSS y JavaScript de MapTiler/MapLibre no aparecen en la respuesta sin aceptar contenido externo.
- La revocación apaga las tres categorías y el script elimina preferencias locales anteriores.
- La configuración productiva exige nombre `__Host-` también para la cookie de preferencias.
- Regresión afectada: 2.080 pruebas aprobadas y 6 omisiones clasificadas; repetición de seguridad/release: 851 aprobadas.

## Riesgos y validación pendiente

- La redacción jurídica, períodos de conservación y clasificación de proveedores requieren F10 y revisión profesional.
- Deben verificarse en staging las restricciones de dominio de MapTiler, CSP, TLS y comportamiento real del proveedor.
- La retirada elimina el almacenamiento local conocido al cargar otra página; los navegadores o extensiones pueden impedir acceso a storage sin afectar el funcionamiento principal.
- No se declara cumplimiento legal definitivo a partir de este control técnico.
