# NGINX estable, no privilegiado y fijado por digest para builds reproducibles.
# Tag: 1.30.4-alpine3.24
# Digest OCI (GHCR): sha256:adf5042a17f4ecdd200c595fa9ffd1be37efb18f89a830bd1a00e4ab4d59d42c
# ES: Rebuild del mismo tag con paquetes Alpine corregidos, validado por el gate Trivy F11.
# EN: Same-tag rebuild with fixed Alpine packages, validated by the F11 Trivy gate.
FROM ghcr.io/nginx/nginx-unprivileged:1.30.4-alpine3.24@sha256:adf5042a17f4ecdd200c595fa9ffd1be37efb18f89a830bd1a00e4ab4d59d42c

LABEL org.opencontainers.image.title="Vinova Pro NGINX" \
      org.opencontainers.image.version="1.0.1" \
      org.opencontainers.image.description="Reverse proxy NGINX no privilegiado para Vinova Pro" \
      org.opencontainers.image.source="https://github.com/nginx/docker-nginx-unprivileged"

USER root

COPY --chown=101:101 templates /opt/vinova/templates
COPY --chown=101:101 entrypoint.sh /usr/local/bin/vinova-nginx-entrypoint

# ES: Fija únicamente las revisiones Alpine que corrigen los CVE detectados por F11.
# EN: Pin only the Alpine revisions that remediate the CVEs detected during F11.
RUN apk add --no-cache --upgrade \
        libexpat=2.8.5-r0 \
        pcre2=10.49-r0 \
        tiff=4.7.2-r0 \
        zlib=1.3.2-r1 \
    && rm -f /etc/nginx/conf.d/default.conf \
    && chmod 0755 /usr/local/bin/vinova-nginx-entrypoint \
    && chown -R 101:101 \
        /etc/nginx/conf.d \
        /opt/vinova/templates \
        /usr/local/bin/vinova-nginx-entrypoint

USER 101:101

EXPOSE 8080 8443

ENTRYPOINT ["/usr/local/bin/vinova-nginx-entrypoint"]
CMD ["nginx", "-g", "daemon off;"]
