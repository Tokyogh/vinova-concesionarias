# B10 — Limpieza segura

Fecha de cierre: 2026-10-15

## Criterio

Sólo se eliminaron archivos versionados clasificados como temporales en B6 o confirmados sin consumidor en B8/B10. Cada ruta se contrastó con referencias del repositorio, scripts de release y pruebas relacionadas. Los archivos eliminados siguen recuperables desde el historial Git.

## Archivos eliminados

| Grupo | Rutas | Motivo |
|---|---|---|
| Reescrituras puntuales | `tmp/fix2.py`, `tmp/fix_utf8.py`, `tmp/fixbom.py`, `tmp/fixmd.py`, `tmp/norm.py`, `tmp/read.py`, `tmp/unify.py` | Scripts sin consumidores que reescribían documentación y podían dañar encoding si se reejecutaban. |
| Salidas transitorias | `tmp/r00/pytest_fail.err`, `tmp/r00/pytest_full.err`, `tmp/r00/pytest_full2.err`, `tmp/r06_pytest.txt` | Logs vacíos/obsoletos sustituidos por informes versionados y resultados reproducibles. |
| Muestra manual de factura | `tmp/pdfs/render_sample.py`, `tmp/pdfs/b6-invoice-sample.pdf`, `tmp/pdfs/b6-invoice-sample.png` | Artefacto aislado sustituido por pruebas automatizadas de facturas y PDF. |
| Nginx heredado | `docker/nginx/default.conf` | Configuración monolítica sin referencias; la imagen elimina el default upstream y usa exclusivamente `templates/http.conf.template` o `templates/https.conf.template` mediante su entrypoint. |

Total: 15 archivos.

## Conservado deliberadamente

- `nd.txt`: DUDOSO y posiblemente personal; no se modificó.
- documentación histórica, roadmaps y evidencia visual LITE→PRO;
- migraciones, fixtures, seeds, licencias y archivos `.gitkeep` estructurales;
- scripts operativos de release, QA, backup, restore y staging;
- `web_carros/`, privados, secretos y el cambio local previo de `.gitignore`.

## Validaciones posteriores

- búsqueda de referencias activas a las 15 rutas: sin consumidores;
- facturas/portal/PDF: 32 pruebas aprobadas y 1 omitida, repetidas después de la eliminación;
- plantillas Nginx HTTP/HTTPS: válidas con Nginx 1.30 en contenedor efímero;
- paquete temporal de release: 1.323 archivos y 1.323 entradas verificadas, checksum SHA-256 generado;
- `manage.py check`: 0 incidencias;
- `makemigrations --check --dry-run`: sin deriva;
- Ruff: aprobado.

## Resultado

La limpieza reduce artefactos sin retirar capacidad operativa ni evidencia histórica necesaria. No se borraron archivos dudosos y no se alteraron datos persistentes.
