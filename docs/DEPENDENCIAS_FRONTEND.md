# Dependencias frontend autocontenidas

Vinova Pro debe continuar operando aunque el concesionario pierda acceso a un
CDN público. Por esa razón HTMX se sirve desde los archivos estáticos de
Django/Nginx.

## HTMX

- Versión fijada: `2.0.10`.
- Ruta de origen: `static/vendor/htmx/htmx.min.js`.
- Licencia incluida: `static/vendor/htmx/LICENSE.txt`.
- Instalación o reparación: `powershell -ExecutionPolicy Bypass -File scripts/install_frontend_dependencies.ps1`.
- Actualización: debe hacerse de forma explícita, con prueba funcional del
  catálogo y de los modales de vehículos.

El instalador de consolidación o `scripts/install_frontend_dependencies.ps1` obtiene el archivo desde la distribución oficial y lo valida con SHA-384:

```text
H5SrcfygHmAuTDZphMHqBJLc3FhssKjG7w/CeCpFReSfwBWDTKpkzPP8c+cLsK+V
```

No debe reemplazarse por una URL remota dentro de las plantillas. El objetivo
es que las pantallas críticas de venta y consulta sigan funcionando dentro de
la red de la concesionaria.

## Google model-viewer

El visor 3D continúa siendo una mejora opcional del catálogo público. Una
futura consolidación puede autocontenerlo junto con sus módulos auxiliares;
si no está disponible, la interfaz conserva las imágenes y fichas normales del
vehículo.
