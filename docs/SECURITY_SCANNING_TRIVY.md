# Escaneo de seguridad con Trivy

## Objetivo

Trivy es un gate previo a staging y a la entrega. No forma parte del runtime de Vinova Pro ni modifica automáticamente dependencias o imágenes.

Revisa:

- vulnerabilidades conocidas y corregibles;
- configuraciones inseguras de Docker e infraestructura;
- vulnerabilidades de imágenes;
- secretos expuestos únicamente cuando se activa esa opción.

## Base NGINX fijada para v2.0.0

La imagen NGINX de Vinova Pro usa una base oficial no privilegiada, estable y fijada por digest:

```text
ghcr.io/nginx/nginx-unprivileged:1.30.4-alpine3.24@sha256:adf5042a17f4ecdd200c595fa9ffd1be37efb18f89a830bd1a00e4ab4d59d42c
```

Contrato esperado:

```text
usuario runtime: uid=101(nginx), gid=101(nginx)
usuario final Dockerfile: 101:101
HTTP interno: 8080
HTTPS interno: 8443
HTTP público: 80
HTTPS público: 443
```

El digest evita que una misma entrega cambie silenciosamente de contenido. Para adoptar una reconstrucción upstream posterior debe actualizarse intencionalmente el tag, el digest, el manifest y la evidencia Trivy. No se usa `apk upgrade` como parche genérico: las revisiones Alpine necesarias se instalan con nombre y versión exactos.

## Gate NGINX consolidado

Este flujo construye sin caché, confirma el UID, ejecuta Trivy de configuración y aplica el gate de vulnerabilidades corregibles de la imagen. Usa `aquasec/trivy:0.76.0` fijado por digest para que la validación sea reproducible. El escaneo de configuración se limita al contexto Nginx y evita recorrer datos locales ajenos al artefacto.

### Windows

```powershell
.\scripts\validate-nginx-security.ps1
```

### Linux o WSL

```bash
./scripts/validate-nginx-security.sh
```

Resultado requerido antes del commit final:

```text
Docker build: aprobado
uid=101(nginx)
misconfig HIGH=0, CRITICAL=0
image vuln --ignore-unfixed HIGH=0, CRITICAL=0
exit_code=0
```

Los reportes JSON se escriben en `security-reports/` y no se incluyen en Git ni en el ZIP.

## Escaneo general del repositorio

### Windows

```powershell
.\scripts\security-scan-trivy.ps1 -Target filesystem -Strict
```

### Linux o WSL

```bash
./scripts/security-scan-trivy.sh filesystem --strict
```

## Escaneo de una imagen ya construida

### Windows

```powershell
.\scripts\security-scan-trivy.ps1 -Target image -Image "vinova-pro-nginx:2.0.0" -Strict
```

### Linux o WSL

```bash
./scripts/security-scan-trivy.sh image --image "vinova-pro-nginx:2.0.0" --strict
```

Por defecto se aplica `--ignore-unfixed`: el gate bloquea vulnerabilidades `HIGH` o `CRITICAL` que sí tienen corrección disponible. Para inventario adicional puede usarse `-IncludeUnfixed` o `--include-unfixed`, pero esos hallazgos deben evaluarse por exposición y no ocultarse mediante excepciones injustificadas.

## Estado de esta entrega

La actualización estática de Dockerfile, digest, UID esperado, puertos, Compose, templates, entrypoint, manifest y scripts está incorporada. En F11 se renovó intencionalmente la base al digest `sha256:adf5042a...` del mismo tag `1.30.4-alpine3.24`. El primer gate actualizado detectó diez HIGH corregibles; el rebuild upstream resolvió siete de `util-linux/libuuid` y se fijaron `libexpat=2.8.5-r0`, `pcre2=10.49-r0`, `tiff=4.7.2-r0` y su revisión de `zlib=1.3.2-r1` para cerrar los tres restantes.

Estado (2026-10-16, Trivy 0.76.0): **passed** con evidencia real reproducida vía `scripts\validate-nginx-security.ps1`:

```text
Docker build: aprobado
uid=101(nginx)
misconfig HIGH=0, CRITICAL=0
image vuln --ignore-unfixed HIGH=0, CRITICAL=0
exit_code=0
```

Reportes JSON conservados en `security-reports/trivy-nginx-config.json` y `security-reports/trivy-nginx-image.json` (excluidos de Git y del ZIP según política de entrega).

## Política de entrega

- `security-reports/`, `trivy-reports/` y `.trivy-cache/` se excluyen del ZIP.
- `nd.txt` se conserva localmente y se excluye del ZIP, Docker, manifest y checksums.
- Trivy no autoriza por sí solo staging ni producción.
- Staging real exige DNS, TLS, servicios externos y smoke sobre el entorno desplegado.
- Producción continúa no autorizada hasta superar el gate de staging y recibir autorización expresa.
