# F11 — Dependencias, CVE y cadena de suministro

Fecha de evidencia local: 2026-10-16

## Alcance e inventario

| Superficie | Inventario verificado | Control aplicado |
|---|---|---|
| Python productivo | 53 paquetes resueltos desde `requirements/production.txt` | `production.lock` fija versión y hashes; Docker usa `pip wheel --require-hashes` |
| JavaScript | no existe gestor npm/yarn/pnpm ni manifiesto de paquetes; los assets propios y vendorizados son estáticos | permanece la validación de sintaxis y el inventario de assets del release |
| aplicación | Python 3.12 slim Bookworm | base fijada por digest y runtime no privilegiado |
| Nginx | Nginx unprivileged 1.30.4 sobre Alpine 3.24 | base por digest, UID 101 y revisiones Alpine fijadas |
| infraestructura local/QA | PostgreSQL 16, Redis 7, Mailpit, MinIO y Playwright | imágenes externas fijadas por digest en Compose/Dockerfile |
| escáner | Trivy 0.76.0 | imagen del escáner fijada por digest en ambos scripts del gate |

Los tags se conservan junto al digest para legibilidad, pero el digest decide el contenido. Las imágenes propias `vinova-pro:*` y `vinova-pro-nginx:*` solo podrán fijarse por digest de registro después de publicarlas; esa evidencia pertenece al gate de staging y no se simuló localmente.

## Lock, hashes y SBOM

`requirements/production.lock` se genera desde los rangos mantenidos:

```powershell
python -m piptools compile --generate-hashes --resolver=backtracking --strip-extras `
  --output-file=requirements/production.lock requirements/production.txt
python -m pip_audit -r requirements/production.lock
```

El build no actualiza `pip` desde Internet y rechaza distribuciones cuyo hash no figure en el lock. El archivo se regenera y revisa; no se edita a mano.

Se generó un SBOM CycloneDX JSON local con 52 componentes de terceros mediante `pip-audit`. La evidencia excluida de Git es `security-reports/vinova-production-sbom.cdx.json`, SHA-256 `2d706fcba2bd24d542389ccadb54be72c569aab06293cabdd5907da8d50639a1`. El lock es la fuente versionada reproducible; el SBOM debe regenerarse para cada release candidato.

## Hallazgos y correcciones

1. La primera imagen de aplicación contenía `web_carros/`, incluido su entorno Python obsoleto, y certificados TLS locales porque el contexto Docker no los excluía. Trivy encontró 13 CVE que pertenecían a LITE y una clave privada local, no al runtime PRO instalado.
2. `.dockerignore` ahora excluye `web_carros` y `docker/nginx/certs/*`, conservando únicamente `.gitkeep`. Una regresión de release exige esas reglas y un probe sobre la imagen confirma que las rutas no existen.
3. La imagen reconstruida quedó con cero vulnerabilidades HIGH/CRITICAL corregibles y cero secretos según Trivy. La clave no está versionada ni se imprimió. Si una imagen previa se hubiera exportado o compartido, la clave correspondiente debe revocarse y rotarse; no existe evidencia de publicación o despliegue durante esta fase.
4. El gate Nginx actualizado detectó diez CVE HIGH corregibles. El nuevo digest upstream resolvió siete de `util-linux/libuuid`; se fijaron revisiones corregidas de `libexpat`, `pcre2`, `tiff` y `zlib`. La repetición quedó en cero HIGH/CRITICAL corregibles.
5. El recorrido completo del workspace con Trivy agotó memoria por directorios locales ajenos al artefacto. El gate se acotó a los contextos realmente empaquetados; la imagen resultante se escanea aparte. No se presenta ese intento incompleto como evidencia aprobada.

## Resultados de herramientas

| Herramienta | Resultado |
|---|---|
| `pip-audit 2.10.1` | 0 vulnerabilidades conocidas en el lock |
| SBOM CycloneDX | 52 componentes; hash registrado arriba |
| `Bandit 1.9.4` | 0 HIGH; 11 MEDIUM y 89 LOW revisados |
| `detect-secrets 1.5.0` | 91 candidatos heurísticos en 64 archivos; ejemplos, fixtures, identificadores y hashes; no se aceptó el conteo como prueba de secretos reales |
| Trivy aplicación | 0 HIGH/CRITICAL corregibles; 0 secretos; `pip check` y Django check aprobados |
| Trivy configuración | 0 misconfiguraciones HIGH/CRITICAL en Docker/Compose |
| Trivy Nginx | UID 101; 0 misconfiguraciones y 0 CVE HIGH/CRITICAL corregibles después de la corrección |

Los avisos MEDIUM de Bandit se revisaron por contexto: URLs generadas por Cloudinary, descarga ASVS desde URL constante con checksum, JUnit producido por la propia suite, literales `/tmp` de runtimes efímeros y bind `0.0.0.0` limitado a settings locales/Gunicorn en contenedor. No se ocultaron con exclusiones globales; deben revaluarse si cambia su límite de confianza.

## Priorización CVE

La priorización combina presencia real en el artefacto, corrección disponible, exposición, impacto y señales externas:

- [NVD](https://nvd.nist.gov/) aporta el registro y métricas normalizadas; al consultar las tres CVE residuales iniciales, dos seguían `Awaiting Analysis` y una `Modified`, por lo que no se usó solo su estado para aplazar la corrección.
- [CISA KEV](https://www.cisa.gov/known-exploited-vulnerabilities-catalog) es la referencia de explotación conocida. La edición `2026.10.15` no contenía ninguna de las diez CVE detectadas.
- [FIRST EPSS](https://www.first.org/epss/) estima probabilidad de explotación observada en los siguientes 30 días y no sustituye impacto ni contexto. Las diez CVE tenían datos el 2026-10-16; el máximo era `0.00553` para CVE-2026-4775.

La ausencia en KEV y los EPSS bajos no justificaron conservar vulnerabilidades corregibles en el reverse proxy expuesto. Se corrigieron todas las encontradas por el gate.

## Procedimiento de actualización segura

1. Modificar rangos únicamente con motivo y changelog revisados.
2. Regenerar el lock con Python 3.12 y hashes.
3. Revisar el diff para detectar paquetes transitivos inesperados.
4. Ejecutar `pip-audit`, generar SBOM y consultar NVD/KEV/EPSS para cada CVE presente.
5. Construir la imagen sin sustituir el lock por archivos de rangos.
6. Ejecutar `pip check`, Django check, pruebas afectadas y Trivy sobre imagen/configuración.
7. Renovar digests de imágenes de forma explícita; nunca volver a tags mutables sin digest.
8. Publicar solo desde el pipeline autorizado y registrar el digest de la imagen propia.

## Riesgos pendientes

- Los paquetes APT del build Python y los repositorios Alpine no usan snapshots de repositorio; las bases y paquetes finales sí quedan controlados por digest/versiones, pero el build aún no es hermético fuera de línea.
- No existe firma/verificación Sigstore del artefacto propio ni attestations verificadas en un registro autorizado.
- El SBOM se conserva como evidencia local excluida de Git; el pipeline de release debe publicarlo junto al artefacto y controlar acceso/retención.
- `detect-secrets` requiere una baseline auditada si se adopta como hook bloqueante; no se debe aceptar automáticamente su salida heurística.
- Los digests de imágenes propias, el registry, la firma y el escaneo posterior a publicación requieren staging/CI reales.

No se declara seguridad absoluta ni autorización productiva con estas verificaciones locales.
