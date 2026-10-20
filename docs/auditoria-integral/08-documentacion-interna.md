# B8 — Documentación interna del código

Fecha de cierre: 2026-10-15
Alcance: fuentes y configuración propios de VINOVA PRO; `web_carros/` permaneció como referencia de solo lectura.

## Criterio aplicado

Los encabezados describen responsabilidad, límites de autorización o papel operativo sin narrar instrucciones obvias. Se preservaron shebangs, declaraciones de encoding y sintaxis de cada formato. Las migraciones históricas, dependencias externas, binarios, archivos generados y `static/vendor/` quedaron excluidos.

En Python se documentaron también las pruebas, por considerarse especificaciones ejecutables. Las clases y funciones públicas de mayor complejidad —100 líneas o más, o al menos 12 estructuras de control— quedaron con docstrings específicos; el barrido final no encontró faltantes bajo ese criterio.

## Cobertura comprobada

| Grupo | Cobertura | Evidencia |
|---|---:|---|
| Python propio | 556/556 módulos | Docstring de módulo válido por AST; incluye aplicación, configuración, scripts, pruebas y `manage.py`. |
| Python complejo | 0 faltantes críticos | Revisión AST de clases y funciones públicas a nivel de módulo. |
| Templates Django | 201/201 | Comentario inicial de responsabilidad y compilación completa con el motor Django. |
| CSS propio | 50/50 | Encabezado de propósito; se conservaron bloques, responsive y estados existentes. |
| JavaScript propio | 5/5 | Encabezado de flujo en scripts propios; `static/vendor/htmx/htmx.min.js` no se tocó. |
| Docker/Nginx activo | 12 archivos revisados | Imágenes, Compose, entrypoints y plantillas explican su papel operativo. |

`docker/nginx/default.conf` es una configuración monolítica heredada que el Dockerfile elimina antes de instalar las plantillas activas. No se reinterpretó en B8; su eliminación o conservación se resolverá con referencias verificadas en B10.

## Validaciones ejecutadas

- `python -m compileall -q apps config scripts`: aprobado.
- `python -m ruff check .`: aprobado.
- `python manage.py check --settings=config.settings.test`: aprobado, 0 incidencias.
- Compilación de las 201 plantillas mediante `django.template.loader.get_template`: aprobada.
- `python scripts/check_javascript.py`: 5 archivos válidos.
- `python scripts/check_nginx_templates.py`: HTTP y HTTPS válidos con Nginx 1.30 y OpenSSL en contenedor efímero; las herramientas no están instaladas en el host Windows.
- Pruebas focales de UI, estabilización, portal e instituciones: 82 aprobadas y 2 omitidas.
- `git diff --check`: aprobado antes de ampliar docstrings y se repite en el cierre del bloque.

## Resultado

La documentación interna cubre las superficies propias compatibles sin modificar reglas de negocio, consultas, rutas, presentación ni controles de seguridad. Los cambios son comentarios, docstrings y normalización de salto final cuando el archivo carecía de él.
