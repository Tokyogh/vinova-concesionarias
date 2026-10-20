# ES: Imagen productiva multietapa; verifica hashes, construye wheels y ejecuta sin privilegios.
# EN: Multi-stage production image; verifies hashes, builds wheels and runs unprivileged.
FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258 AS builder

ARG REQUIREMENTS_FILE=production.lock
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements ./requirements
RUN python -m pip wheel --require-hashes --wheel-dir /wheels -r "requirements/${REQUIREMENTS_FILE}"

# ES: La etapa siguiente separa dependencias, artefactos y privilegios del runtime.
# EN: The following stage separates dependencies, artifacts, and runtime privileges.
FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258 AS runtime

ARG APP_UID=10001
ARG APP_GID=10001
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    VINOVA_SHARED_ASSETS_GID=101 \
    PATH="/home/vinova/.local/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl --fail --silent --show-error \
        -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
        https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    && . /etc/os-release \
    && printf '%s\n' \
        'Types: deb' \
        'URIs: https://apt.postgresql.org/pub/repos/apt' \
        "Suites: ${VERSION_CODENAME}-pgdg" \
        "Architectures: $(dpkg --print-architecture)" \
        'Components: main' \
        'Signed-By: /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc' \
        > /etc/apt/sources.list.d/pgdg.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        postgresql-client-16 \
        zlib1g \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid "${APP_GID}" vinova \
    && useradd --uid "${APP_UID}" --gid vinova --create-home --shell /usr/sbin/nologin vinova

COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/* && rm -rf /wheels

WORKDIR /app
COPY --chown=vinova:vinova . /app
COPY --chown=root:root docker/entrypoint.sh /usr/local/bin/vinova-entrypoint
RUN chmod 0755 /usr/local/bin/vinova-entrypoint \
    && mkdir -p /app/staticfiles /app/media /app/private /app/logs /app/run \
    && chown -R "${APP_UID}:101" /app/staticfiles /app/media \
    && chmod 2750 /app/staticfiles /app/media \
    && chown -R vinova:vinova /app/private /app/logs /app/run \
    && chmod 0700 /app/private /app/logs /app/run

USER vinova
EXPOSE 8000
ENTRYPOINT ["/usr/local/bin/vinova-entrypoint"]
CMD ["gunicorn", "-c", "config/gunicorn.conf.py", "config.wsgi:application"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD test "$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
        --header "Host: ${VINOVA_HEALTHCHECK_HOST:-localhost}" \
        --header "X-Forwarded-Proto: https" \
        http://127.0.0.1:8000/health/live/)" = "200"
