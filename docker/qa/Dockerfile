# ES: Imagen exclusiva de QA con navegadores y clientes de base de datos; nunca es runtime productivo.
# EN: QA-only image with browsers and database clients; never a production runtime.
FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258 AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY requirements ./requirements
RUN python -m pip install --upgrade pip \
    && python -m pip wheel --wheel-dir /wheels -r requirements/local.txt

FROM mcr.microsoft.com/playwright:v1.60.0-noble@sha256:9bd26ad900bb5e0f4dee75839e957a89ae89c2b7ab1e76050e559790e946b948 AS runtime

ARG QA_UID=10002
ARG QA_GID=10002
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" \
    DJANGO_SETTINGS_MODULE=config.settings.test \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gettext-base nginx postgresql-client-16 python3 python3-venv \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid "${QA_GID}" vinovaqa \
    && useradd --uid "${QA_UID}" --gid vinovaqa --create-home --shell /usr/sbin/nologin vinovaqa \
    && python3 -m venv "${VIRTUAL_ENV}"

COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir /wheels/* \
    && python -c "import django, playwright, psycopg; print('QA Python runtime OK')" \
    && PLAYWRIGHT_BROWSERS_PATH=/ms-playwright python -c "from pathlib import Path; from playwright.sync_api import sync_playwright; p=sync_playwright().start(); paths={name: Path(getattr(p, name).executable_path) for name in ('chromium','firefox','webkit')}; p.stop(); missing={name: str(path) for name, path in paths.items() if not path.is_file()}; assert not missing, f'Playwright browsers missing: {missing}'; print('QA Playwright browsers OK')" \
    && rm -rf /wheels

WORKDIR /app
COPY --chown=vinovaqa:vinovaqa . /app
RUN mkdir -p /app/private/qa_reports /tmp/vinova-qa-runtime /tmp/vinova-qa-cache/ruff /tmp/vinova-qa-cache/pytest \
    && chown -R vinovaqa:vinovaqa /app/private/qa_reports /tmp/vinova-qa-runtime /tmp/vinova-qa-cache

USER vinovaqa
CMD ["python", "manage.py", "run_quality_checks", "--profile", "quick"]
