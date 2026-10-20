# B6 — Inventario documental y de artefactos

Fecha: 2026-10-15

## Resultado

En el corte inicial se inventariaron 1.230 archivos versionados y 114 archivos documentales o de
evidencia fuera de código/templates/static/LITE. `docs/` contenía 93 archivos:
71 documentos Markdown/JSON y 22 artefactos visuales o auxiliares. No se borró
nada en este bloque.

Los archivos locales `.env` y `.env.staging` están fuera de Git y se clasifican
como **privados protegidos**; no se leyó ni reprodujo su contenido. El cambio
local preexistente en `.gitignore` sigue sin incluirse en los commits.

## Clasificación por conjunto

| Conjunto | Cantidad | Clasificación | Acción segura |
|---|---:|---|---|
| `README.md` y `docs/README.md` | 2 | REEMPLAZABLE | regenerar en B7 y conservar como puntos de entrada canónicos |
| documentación técnica raíz de `docs/` | 27 | VIGENTE / REEMPLAZABLE | contrastar y consolidar en B7; no eliminar hasta sustituir referencias |
| `docs/auditoria-integral/` | 7 con este inventario | VIGENTE | fuente del estado demostrado por esta auditoría |
| `docs/integracion-lite-pro/` | 15 | HISTÓRICO NECESARIO | conservar como trazabilidad de integración; marcar sus checkpoints como cerrados, no actuales |
| `docs/vinova-redesign/` | 12 | HISTÓRICO NECESARIO | conservar decisiones, inventario visual y reportes R00–R06 |
| `docs/ui/` y `docs/ui/panels/` | 14 | HISTÓRICO NECESARIO / REFERENCIA | conservar: geometría, specs y 9 imágenes son evidencia visual LITE→PRO |
| `docs/manuals/` | 17 | VIGENTE, sujeto a actualización | reutilizar como base operativa y enlazar desde el índice nuevo |
| `docs/CHANGELOG.md` | 1 | HISTÓRICO NECESARIO | conservar; no reescribir retrospectivamente |
| ejemplos `.env.*.example` | 3 | VIGENTE | conservar; documentan variables sin secretos |
| `deployment/role-credentials.example.json` | 1 | VIGENTE | conservar como esquema sintético; no contiene credenciales reales |
| `scripts/staging-bot-revision.txt` | 1 | VIGENTE AUXILIAR | consumido por tooling de staging; conservar |
| `nd.txt` | 1 | DUDOSO / POSIBLE ARCHIVO PERSONAL | contiene instrucciones Git antiguas y riesgosas (`git add .`/stash), pero está referenciado por exclusiones de release y documentos históricos; no borrar sin decisión explícita |
| `tmp/` versionado | 14 | TEMPORAL | candidatos de eliminación B10 tras confirmar sustitución y diff |
| `run/.gitkeep`, `private/.gitkeep` | 2 | VIGENTE ESTRUCTURAL | conservar para crear directorios ignorados sin versionar resultados/secretos |

## Documentación técnica raíz

### Vigente y reusable

- instalación/configuración/operación: `INSTALACION.md`, `CONFIGURACION.md`,
  `PRODUCCION.md`, `OPERACION.md`, `ACTUALIZACION.md`, `LIFECYCLE.md`;
- arquitectura/producto: `ARQUITECTURA.md`, `MODULOS.md`,
  `DEPENDENCIAS_FRONTEND.md`, `UI_UX_V200.md`;
- seguridad/continuidad: `SECURITY.md`, `SECURITY_SCANNING_TRIVY.md`,
  `BACKUPS.md`, `EMERGENCY_RECOVERY.md`, `TRANSFER.md`;
- API/BI: `API.md`, `POWER_BI.md`;
- QA/despliegue: `QA_FULL_V200.md`, `DEPLOYMENT_SMOKE_BOT.md`,
  `DEPLOYMENT_SMOKE_ROLE_MATRIX.md`, `CI_CD_DEPLOYMENT_SMOKE.md`;
- historial: `CHANGELOG.md`.

Estos documentos tienen valor operativo, pero parte de sus cifras, rangos de
dependencias y resultados corresponden a cortes anteriores. B7 debe actualizar
los hechos vigentes y evitar que se interpreten como una certificación actual.

### Reemplazables tras B7

- `VINOVA_PRO_MASTER_DOCUMENTATION.md`: compendio amplio, parcialmente
  duplicado por documentos modulares;
- `VINOVA_PRO_FINAL_REPORT.md` y `VINOVA_NEXT_CLOSURE_REPORT.md`: informes de
  cierres anteriores que deben pasar a categoría histórica al existir el
  informe final B12 de esta auditoría;
- `ROADMAP.md`: roadmap cerrado/anterior; debe conservarse como histórico o
  enlazarse claramente desde el nuevo estado, no presentarse como trabajo
  activo;
- `UPDATE_ARCHITECTURE.md`: conservar contenido técnico, integrándolo en
  arquitectura/operación para evitar dos fuentes de verdad.

No se autoriza su eliminación automática: primero se actualizarán enlaces y se
verificará que el documento sustituto cubra su información única.

## Checkpoints históricos

`ROADMAP_ACTIVO.md`, `CERTIFICACION_ACTIVA.md` y `PARIDAD_ACTIVA.md` bajo
`docs/integracion-lite-pro/` son evidencia cerrada de trabajos anteriores. Sus
HEADs, cifras y “siguiente acción” no representan el checkpoint actual. El único
checkpoint activo de esta misión es `docs/auditoria-integral/ESTADO_ACTIVO.md`.

Se conservan porque prueban decisiones y gates externos (Cloudinary, staging,
TLS y aprobación visual) que todavía importan. B7 debe etiquetarlos como
históricos desde los índices, no reescribirlos.

## Artefactos temporales versionados

| Ruta | Evidencia | Referencias | Clasificación B10 |
|---|---|---|---|
| `tmp/fix2.py`, `fix_utf8.py`, `fixbom.py`, `fixmd.py`, `norm.py`, `read.py`, `unify.py` | scripts puntuales que reescribían `AGENTS.md`/docs | ninguna | eliminar: obsoletos y peligrosos si se reejecutan |
| `tmp/r00/pytest_fail.err`, `pytest_full.err`, `pytest_full2.err` | salidas vacías o error “e2e no encontrado” | ninguna | eliminar: evidencia reemplazada |
| `tmp/r06_pytest.txt` | salida Pytest de 65.829 bytes | ninguna; R06 resume el resultado | eliminar: sustituido por phase report y Git |
| `tmp/pdfs/render_sample.py`, `b6-invoice-sample.pdf`, `b6-invoice-sample.png` | prueba manual de PDF de factura | solo referencia interna entre esos archivos | eliminar si las pruebas automatizadas de PDF siguen verdes |

Los 14 archivos estaban ya versionados en la base recibida. No son cambios
ajenos sin rastrear; aun así, su eliminación se pospone a B10 y tendrá commit
separado.

## Archivos conservados deliberadamente

- migraciones y fixtures: evidencia histórica ejecutable;
- imágenes/specs de `docs/ui`: baseline visual y geometría;
- manuales e informes por fase: decisiones y resultados no recuperables solo
  desde el código;
- scripts operativos de backup, restore, QA, staging y release: tienen
  consumidores o valor operacional;
- `.gitkeep`: estructura de almacenamiento privado/runtime;
- `AGENTS.md`: instrucciones actuales del repositorio;
- `nd.txt`: dudoso/posiblemente personal; se excluye de limpieza automática.

## Verificaciones para B10

Antes de eliminar cada candidato temporal:

1. ejecutar `git grep` para referencias nuevamente;
2. comprobar que no forma parte de scripts de release;
3. ejecutar pruebas de factura PDF para el grupo `tmp/pdfs`;
4. confirmar que `web_carros/`, `.gitignore`, archivos privados y documentación
   histórica no aparecen en el diff;
5. registrar ruta y motivo en el informe final.
