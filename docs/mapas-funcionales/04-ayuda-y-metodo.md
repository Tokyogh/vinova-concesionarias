# Mapa funcional — Ayuda contextual y método de evidencia

## Centro de ayuda

Evidencia: [14-ayuda-contextual.png](capturas/14-ayuda-contextual.png)

Ruta: `/dashboard/help/`

`HelpHomeView` utiliza `visible_articles_for_user`. El selector empieza por artículos publicados cuya categoría está activa, aplica la búsqueda sobre título, resumen, contenido, palabras clave y categoría, y finalmente comprueba `permission_code` y `role_codes` con `resource_visible_to_user`. El usuario necesita `help.view` o `help.manage`; `is_staff` por sí solo no concede acceso.

| Componente señalado | Información | Vacío y control |
|---|---|---|
| Búsqueda | Campos de `HelpArticle` visibles para el usuario. | Sin coincidencias muestra resultado vacío; no busca en borradores ni contenido no autorizado. |
| Artículos destacados | `is_featured`, `title`, `summary`, `article_type`, `estimated_minutes`. | Solo artículos publicados de categorías activas y permitidos por rol/permiso. |
| Biblioteca | `HelpCategory.order`, `HelpArticle.order` y contenido visible. | Categorías inactivas y artículos despublicados no aparecen. |

La gestión separada exige `help.manage` y permite crear, editar, previsualizar, publicar, despublicar, consultar historial y restaurar. `create_help_article`, `update_help_article`, `set_help_article_publication` y `restore_help_article_version` usan transacciones; las actualizaciones bloquean la fila, guardan una instantánea `HelpArticleVersion` y emiten auditoría. Restaurar crea una versión nueva: no borra ni reescribe el historial.

## Cómo se produjo la evidencia

`tests/e2e/test_12_functional_maps.py`:

1. Arranca el servidor de prueba y una base temporal.
2. Crea compañía, sede, cuentas, permisos, cliente, vehículo y registros de dominio sintéticos.
3. Habilita `post_sales` solo para el escenario y registra consentimiento temporal de medios externos.
4. Abre cada URL real con Chromium y exige HTTP 200.
5. Comprueba que cada selector señalado existe y que no hay overflow horizontal del documento.
6. Inserta badges y una leyenda temporal en el DOM, captura la página completa y elimina el overlay.
7. Verifica que el conjunto final contiene exactamente las 15 imágenes esperadas.

El escenario puede ejecutarse con `scripts/qa-e2e.ps1 maps chromium`; `scripts/run_e2e.py` resuelve el alias `maps` al módulo E2E. La evidencia aprobada queda en `docs/mapas-funcionales/capturas/` y las trazas, videos o fallos permanecen fuera de Git bajo `private/qa_reports/`.

## Límites de la evidencia

- Confirma rutas, componentes, datos derivados, fallbacks y controles ejercitados localmente.
- No sustituye la revisión humana de usabilidad ni la aprobación visual empresarial.
- No acredita disponibilidad, cuota, DNS, TLS o restricciones de dominio de MapTiler en staging/producción.
- No afirma cumplimiento legal definitivo ni condición `PRODUCTION READY`.
