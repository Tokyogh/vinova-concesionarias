# Avisos de componentes de terceros

VINOVA PRO incluye o utiliza componentes desarrollados por terceros. Esos
componentes no quedan cubiertos por la licencia propietaria del código propio y
mantienen sus licencias y avisos originales.

## Componente redistribuido en el repositorio

| Componente | Ubicación | Licencia verificada | Aviso local |
|---|---|---|---|
| HTMX | `static/vendor/htmx/htmx.min.js` | Zero-Clause BSD | [`static/vendor/htmx/LICENSE.txt`](static/vendor/htmx/LICENSE.txt) |

El texto original de la licencia se conserva junto al componente y no debe
eliminarse en una distribución.

## Dependencias instaladas durante el despliegue

Las dependencias Python se declaran en `requirements/` y se resuelven mediante
el lock productivo. Cada paquete conserva la licencia publicada por su autor.
Antes de distribuir una imagen, instalador o paquete autónomo, se debe:

1. generar el SBOM del artefacto exacto;
2. verificar versiones, licencias y obligaciones de redistribución;
3. incorporar los avisos exigidos por cada dependencia; y
4. conservar separadas las condiciones del código propio y de terceros.

Este inventario cubre el componente frontend versionado directamente en el
repositorio. No sustituye la revisión jurídica ni el inventario del artefacto
final construido.
