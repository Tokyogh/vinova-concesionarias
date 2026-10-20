"""ES: Este módulo implementa el componente release checks para el dominio de infraestructura compartida.

EN: This module implements the release checks component for the common domain.

Contexto existente / Existing context:
Release checks support for the common domain.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from django.conf import settings
from django.urls import NoReverseMatch, Resolver404, URLPattern, URLResolver, get_resolver, resolve, reverse

CRITICAL_TASKS = {
    "apps.common.tasks.system_heartbeat",
    "apps.continuity.tasks.run_backup_task",
    "apps.continuity.tasks.schedule_policy_backups",
    "apps.api.tasks.deliver_webhook_task",
    "apps.quality.tasks.run_quality_profile_task",
    "apps.quality.tasks.schedule_automated_quality_run",
}

CRITICAL_ROUTES = {
    "health-live": "/health/live/",
    "health-ready": "/health/ready/",
    "health-dependencies": "/health/dependencies/",
    "dashboard:home": "/",
    "dashboard:staff_home": "/dashboard/",
    "accounts:login": "/accounts/login/",
    "accounts:profile": "/accounts/profile/",
    "security_center:dashboard": "/dashboard/security/",
    "vehicles:catalog": "/vehicles/",
    "leads:public_request": "/leads/request/",
    "privacy_public:cookie_settings": "/privacy/cookies/",
    "privacy_public:privacy_policy": "/privacy/policy/",
    "privacy_public:terms": "/privacy/terms/",
    "privacy_public:request": "/privacy/request/",
    "vehicles_internal:list": "/dashboard/vehicles/",
    "customers_internal:list": "/dashboard/customers/",
    "inventory_internal:list": "/dashboard/inventory/",
    "sales_internal:list": "/dashboard/sales/",
    "documents_internal:list": "/dashboard/documents/",
    "invoices_internal:list": "/dashboard/invoices/",
    "notifications_internal:inbox": "/dashboard/notifications/",
    "reports_internal:home": "/dashboard/reports/",
    "leads_internal:list": "/dashboard/leads/",
    "analytics_internal:home": "/dashboard/analytics/",
    "audit_internal:list": "/dashboard/audit/",
    "continuity:dashboard": "/dashboard/continuity/",
    "privacy:dashboard": "/dashboard/privacy/",
    "imports_internal:home": "/dashboard/imports/",
    "enterprise:home": "/dashboard/company/",
    "api_internal:dashboard": "/dashboard/integrations/",
    "help_center:home": "/dashboard/help/",
    "quality:run_list": "/dashboard/quality/",
    "api_v1:quality-api:run_list": "/api/v1/quality/runs/",
    "schema": "/api/schema/",
    "swagger-ui": "/api/docs/",
    "schema-v1": "/api/v1/schema/",
    "swagger-ui-v1": "/api/v1/docs/",
}

REQUIRED_RELEASE_FILES = {
    "README.md",
    ".env.example",
    ".env.production.example",
    ".env.staging.example",
    "Dockerfile",
    "requirements/production.lock",
    "docker-compose.yml",
    "docker-compose.prod.yml",
    "docker-compose.staging.yml",
    "docker-compose.qa.yml",
    "docker-compose.qa-cli.yml",
    "docker/qa/Dockerfile",
    "apps/quality/migrations/0001_initial.py",
    "docs/README.md",
    "docs/INSTALACION.md",
    "docs/PRODUCCION.md",
    "docs/CONFIGURACION.md",
    "docs/ROLES_PERMISOS.md",
    "docs/MODULOS.md",
    "docs/OPERACION.md",
    "docs/SECURITY.md",
    "docs/BACKUPS.md",
    "docs/EMERGENCY_RECOVERY.md",
    "docs/ACTUALIZACION.md",
    "docs/CHANGELOG.md",
    "docs/API.md",
    "docs/ARQUITECTURA.md",
    "docs/DEPLOYMENT_SMOKE_BOT.md",
    "docs/manuals/README.md",
    "scripts/build_release_zip.py",
    "scripts/validate_release.sh",
    "scripts/validate_release.ps1",
    "scripts/vinova-qa.sh",
    "scripts/vinova-qa.ps1",
    "scripts/vinova-qa.cmd",
    "scripts/qa-e2e.sh",
    "scripts/qa-e2e.ps1",
    "scripts/qa-e2e.cmd",
    "scripts/qa-full.sh",
    "scripts/qa-full.cmd",
    "scripts/qa-release.sh",
    "scripts/qa-release.cmd",
    "scripts/vinova_qa.py",
    "scripts/check_nginx_templates.py",
    "scripts/check_javascript.py",
    "scripts/check_release_package.py",
    "scripts/cleanup-obsolete-qa.ps1",
}

URL_TAG_RE = re.compile(r"\{%\s*url\s+['\"]([^'\"]+)['\"]")
INLINE_SCRIPT_RE = re.compile(r"<script\b(?![^>]*\bsrc\s*=)[^>]*>", re.IGNORECASE)
INLINE_EVENT_RE = re.compile(r"\son[a-z]+\s*=", re.IGNORECASE)
EXTERNAL_SCRIPT_RE = re.compile(r"<script\b[^>]*\bsrc=['\"](https://[^'\"]+)['\"]", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class ReleaseCheckResult:
    code: str
    level: str
    message: str

    @property
    def ok(self) -> bool:
        return self.level == "ok"


def _ok(code: str, message: str) -> ReleaseCheckResult:
    return ReleaseCheckResult(code=code, level="ok", message=message)


def _error(code: str, message: str) -> ReleaseCheckResult:
    return ReleaseCheckResult(code=code, level="error", message=message)


def _warning(code: str, message: str) -> ReleaseCheckResult:
    return ReleaseCheckResult(code=code, level="warning", message=message)


def _iter_named_patterns(patterns, namespaces: tuple[str, ...] = ()):
    for pattern in patterns:
        if isinstance(pattern, URLPattern):
            if pattern.name:
                yield ":".join((*namespaces, pattern.name))
            continue
        if isinstance(pattern, URLResolver):
            child_namespaces = namespaces + ((pattern.namespace,) if pattern.namespace else ())
            yield from _iter_named_patterns(pattern.url_patterns, child_namespaces)


def check_critical_routes() -> list[ReleaseCheckResult]:
    failures: list[str] = []
    for route_name, expected_path in CRITICAL_ROUTES.items():
        try:
            actual_path = reverse(route_name)
            match = resolve(actual_path)
        except (NoReverseMatch, Resolver404) as exc:
            failures.append(f"{route_name}: {exc.__class__.__name__}")
            continue
        if actual_path != expected_path:
            failures.append(f"{route_name}: {actual_path} (esperada {expected_path})")
        elif match.view_name != route_name:
            failures.append(f"{route_name}: resolve devolvió {match.view_name}")
    if failures:
        return [_error("routes.critical", "Rutas críticas inconsistentes: " + "; ".join(failures))]
    return [_ok("routes.critical", f"{len(CRITICAL_ROUTES)} rutas críticas revierten y resuelven correctamente.")]


def check_template_routes() -> list[ReleaseCheckResult]:
    root = Path(settings.BASE_DIR)
    known_names = set(_iter_named_patterns(get_resolver().url_patterns))
    missing: list[str] = []
    references = 0
    for template in sorted(root.glob("templates/**/*.html")):
        text = template.read_text(encoding="utf-8")
        for route_name in URL_TAG_RE.findall(text):
            references += 1
            if route_name not in known_names:
                missing.append(f"{template.relative_to(root)} -> {route_name}")
    if missing:
        return [_error("routes.templates", "Referencias de plantilla inexistentes: " + "; ".join(missing))]
    return [_ok("routes.templates", f"{references} referencias URL literales apuntan a nombres registrados.")]


def check_template_script_policy() -> list[ReleaseCheckResult]:
    root = Path(settings.BASE_DIR)
    inline: list[str] = []
    unpinned: list[str] = []
    for template in sorted(root.glob("templates/**/*.html")):
        text = template.read_text(encoding="utf-8")
        relative = template.relative_to(root)
        if INLINE_SCRIPT_RE.search(text) or INLINE_EVENT_RE.search(text):
            inline.append(str(relative))
        for url in EXTERNAL_SCRIPT_RE.findall(text):
            package = url.split("/", 3)[-1]
            if "@" not in package:
                unpinned.append(f"{relative}: {url}")
    results: list[ReleaseCheckResult] = []
    if inline:
        results.append(_error("security.inline_scripts", "Scripts o eventos inline: " + ", ".join(inline)))
    else:
        results.append(_ok("security.inline_scripts", "Las plantillas no requieren script-src 'unsafe-inline'."))
    if unpinned:
        results.append(_error("security.external_scripts", "Scripts externos sin versión fija: " + "; ".join(unpinned)))
    else:
        results.append(_ok("security.external_scripts", "Los scripts externos usan versiones explícitas."))
    return results


def check_version_consistency() -> list[ReleaseCheckResult]:
    root = Path(settings.BASE_DIR)
    version = settings.VINOVA_PRODUCT_VERSION
    failures: list[str] = []
    if settings.SPECTACULAR_SETTINGS.get("VERSION") != version:
        failures.append("SPECTACULAR_SETTINGS.VERSION")

    expected_tokens = {
        "docker-compose.prod.yml": [f"vinova-pro:{version}", f"vinova-pro-nginx:{version}"],
        "templates/components/head_assets.html": ["?v={{ vinova_product_version }}"],
        ".env.example": [f"SENTRY_RELEASE=vinova-pro@{version}"],
        ".env.production.example": [f"SENTRY_RELEASE=vinova-pro@{version}"],
    }
    for filename, tokens in expected_tokens.items():
        text = (root / filename).read_text(encoding="utf-8")
        failures.extend(f"{filename}: falta {token}" for token in tokens if token not in text)
    if failures:
        return [_error("version.consistency", "Versiones inconsistentes: " + "; ".join(failures))]
    return [_ok("version.consistency", f"Versión {version} coherente en Django, OpenAPI, Docker y assets.")]


def check_celery_configuration() -> list[ReleaseCheckResult]:
    """ES: Ejecuta la operación «check celery configuration» dentro del dominio de infraestructura compartida.

    EN: Executes the «check celery configuration» operation within the common domain.
    """

    from apps.api.tasks import deliver_webhook_task
    from apps.common.tasks import system_heartbeat
    from apps.continuity.tasks import run_backup_task, schedule_policy_backups
    from apps.quality.tasks import (
        cleanup_quality_evidence_task,
        run_quality_profile_task,
        schedule_automated_quality_run,
    )

    registered = {
        system_heartbeat.name,
        run_backup_task.name,
        schedule_policy_backups.name,
        deliver_webhook_task.name,
        run_quality_profile_task.name,
        schedule_automated_quality_run.name,
        cleanup_quality_evidence_task.name,
    }
    failures: list[str] = []
    missing = sorted(CRITICAL_TASKS - registered)
    if missing:
        failures.append(f"tareas no importables: {missing}")

    expected_routes = {
        "apps.continuity.tasks.run_backup_task": settings.CELERY_BACKUP_QUEUE,
        "apps.api.tasks.deliver_webhook_task": settings.CELERY_WEBHOOK_QUEUE,
        "apps.quality.tasks.run_quality_profile_task": settings.CELERY_QA_QUEUE,
    }
    for task_name, queue in expected_routes.items():
        configured = settings.CELERY_TASK_ROUTES.get(task_name, {}).get("queue")
        if configured != queue:
            failures.append(f"{task_name} usa cola {configured!r}, esperada {queue!r}")

    beat_tasks = {entry.get("task") for entry in settings.CELERY_BEAT_SCHEDULE.values()}
    for task_name in {
        "apps.common.tasks.system_heartbeat",
        "apps.continuity.tasks.schedule_policy_backups",
        "apps.quality.tasks.schedule_automated_quality_run",
        "apps.quality.tasks.cleanup_quality_evidence_task",
    }:
        if task_name not in beat_tasks:
            failures.append(f"Beat no programa {task_name}")

    if settings.VINOVA_QA_MAX_CONCURRENT_RUNS < 1:
        failures.append("VINOVA_QA_MAX_CONCURRENT_RUNS debe ser al menos 1")
    if settings.VINOVA_QA_STALE_AFTER_MINUTES * 60 <= settings.VINOVA_QA_HARD_TIME_LIMIT:
        failures.append("VINOVA_QA_STALE_AFTER_MINUTES debe superar el límite duro de la tarea QA")
    if settings.VINOVA_QA_RETENTION_DAYS < 1:
        failures.append("VINOVA_QA_RETENTION_DAYS debe ser al menos 1")

    if failures:
        return [_error("celery.configuration", "Configuración Celery inconsistente: " + "; ".join(failures))]
    return [_ok("celery.configuration", "Tareas críticas, colas y programación Beat son coherentes.")]


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def check_docker_configuration() -> list[ReleaseCheckResult]:
    """Comprueba los contratos Docker de release. / Check Docker release contracts."""

    root = Path(settings.BASE_DIR)
    failures: list[str] = []
    local = _load_yaml(root / "docker-compose.yml")
    production = _load_yaml(root / "docker-compose.prod.yml")
    qa = _load_yaml(root / "docker-compose.qa.yml")
    qa_cli = _load_yaml(root / "docker-compose.qa-cli.yml")

    local_required = {"db", "redis", "mailpit", "web", "celery_worker", "celery_beat"}
    production_required = {"redis", "app_init", "web", "celery_worker", "celery_beat", "nginx"}
    qa_required = {"qa_db", "qa_redis", "qa_runner", "qa_worker"}
    local_services = set(local.get("services", {}))
    production_services = set(production.get("services", {}))
    qa_services = set(qa.get("services", {}))
    qa_cli_services = set(qa_cli.get("services", {}))
    if missing := sorted(local_required - local_services):
        failures.append(f"Compose local sin servicios {missing}")
    if missing := sorted(production_required - production_services):
        failures.append(f"Compose producción sin servicios {missing}")
    if missing := sorted(qa_required - qa_services):
        failures.append(f"Compose QA sin servicios {missing}")
    if qa_cli_services != {"qa_db", "qa_redis", "qa_runner"}:
        failures.append("Compose QA CLI debe contener únicamente qa_db, qa_redis y qa_runner")

    # ES: Los servicios de terceros deben ser reproducibles; una etiqueta por sí sola es mutable.
    # EN: Third-party services must be reproducible; a tag on its own is mutable.
    external_images = {
        "docker-compose.yml": (local, {"db", "redis", "mailpit", "minio"}),
        "docker-compose.prod.yml": (production, {"db", "redis"}),
        "docker-compose.qa.yml": (qa, {"qa_db", "qa_redis"}),
        "docker-compose.qa-cli.yml": (qa_cli, {"qa_db", "qa_redis"}),
    }
    digest_pattern = re.compile(r"@sha256:[0-9a-f]{64}$")
    for compose_name, (compose, service_names) in external_images.items():
        services = compose.get("services", {})
        for service_name in service_names:
            service = services.get(service_name, {})
            if not service:
                continue
            image = str(service.get("image", ""))
            if not digest_pattern.search(image):
                failures.append(f"{compose_name}:{service_name} no fija la imagen externa por digest SHA-256")


    cli_runner = qa_cli.get("services", {}).get("qa_runner", {})
    if "env_file" in cli_runner:
        failures.append("qa_runner CLI no debe cargar el .env empresarial")
    cli_command = str(cli_runner.get("command", ""))
    if "scripts/vinova_qa.py" not in cli_command or "run_quality_checks" in cli_command:
        failures.append("qa_runner CLI no usa el ejecutor standalone")
    if set(cli_runner.get("depends_on", {})) != {"qa_db", "qa_redis"}:
        failures.append("qa_runner CLI tiene dependencias distintas de qa_db y qa_redis")
    if "qa_internal" not in cli_runner.get("networks", []):
        failures.append("qa_runner CLI no usa la red QA interna")
    cli_network = qa_cli.get("networks", {}).get("qa_internal", {})
    if not cli_network.get("internal"):
        failures.append("La red qa_internal del Compose CLI no está marcada como interna")
    cli_environment = cli_runner.get("environment", {})
    for variable in ("VINOVA_QA_RUNTIME_ROOT", "RUFF_CACHE_DIR", "XDG_CACHE_HOME"):
        if not str(cli_environment.get(variable, "")).startswith("/tmp/"):
            failures.append(f"qa_runner CLI no dirige {variable} a un runtime temporal")
    if "cache_dir=/tmp/" not in str(cli_environment.get("PYTEST_ADDOPTS", "")):
        failures.append("qa_runner CLI no dirige la caché Pytest a /tmp")
    if cli_environment.get("VINOVA_QA_PLAYWRIGHT_BROWSERS_PATH") != "/ms-playwright":
        failures.append("qa_runner CLI no fija el almacén oficial de navegadores Playwright")
    if any("/app/run/qa" in str(item) for item in cli_runner.get("tmpfs", [])):
        failures.append("qa_runner CLI monta /app/run/qa con permisos no deterministas")
    for service_name in ("qa_db", "qa_redis"):
        service = qa_cli.get("services", {}).get(service_name, {})
        if service.get("ports"):
            failures.append(f"{service_name} del Compose CLI publica puertos")

    qa_runner = qa.get("services", {}).get("qa_runner", {})
    qa_worker = qa.get("services", {}).get("qa_worker", {})
    for service_name, service in (("qa_runner", qa_runner), ("qa_worker", qa_worker)):
        if "qa" not in service.get("profiles", []):
            failures.append(f"{service_name} no está aislado tras el perfil qa")
        volumes = [str(volume) for volume in service.get("volumes", [])]
        if any(volume.endswith(":/app") or volume.endswith(":/app:rw") for volume in volumes):
            failures.append(f"{service_name} monta el código de la empresa con escritura")
        if any("docker.sock" in volume for volume in volumes):
            failures.append(f"{service_name} monta el socket de Docker")
        if "no-new-privileges:true" not in service.get("security_opt", []):
            failures.append(f"{service_name} no activa no-new-privileges")
        if "ALL" not in service.get("cap_drop", []):
            failures.append(f"{service_name} no elimina capacidades Linux")
        if "qa_internal" not in service.get("networks", []):
            failures.append(f"{service_name} no usa la red QA interna")
        service_environment = service.get("environment", {})
        if not str(service_environment.get("VINOVA_QA_RUNTIME_ROOT", "")).startswith("/tmp/"):
            failures.append(f"{service_name} no usa runtime temporal escribible")
        if not str(service_environment.get("RUFF_CACHE_DIR", "")).startswith("/tmp/"):
            failures.append(f"{service_name} no usa caché Ruff temporal")
        if "cache_dir=/tmp/" not in str(service_environment.get("PYTEST_ADDOPTS", "")):
            failures.append(f"{service_name} no usa caché Pytest temporal")
        if service_environment.get("VINOVA_QA_PLAYWRIGHT_BROWSERS_PATH") != "/ms-playwright":
            failures.append(f"{service_name} no fija el almacén oficial de navegadores Playwright")
        if any("/app/run/qa" in str(volume) for volume in service.get("volumes", [])):
            failures.append(f"{service_name} monta el runtime bajo /app")
        dependencies = set(service.get("depends_on", {}))
        if "db" in dependencies:
            failures.append(f"{service_name} depende del PostgreSQL empresarial")
        for dependency in {"qa_db", "qa_redis"}:
            if dependency not in dependencies:
                failures.append(f"{service_name} no espera el servicio {dependency}")

    qa_worker_command = str(qa_worker.get("command", ""))
    if "-Q qa" not in qa_worker_command or "--concurrency=1" not in qa_worker_command:
        failures.append("qa_worker no está limitado a la cola qa con concurrencia uno")
    qa_db = qa.get("services", {}).get("qa_db", {})
    qa_redis = qa.get("services", {}).get("qa_redis", {})
    if "/var/lib/postgresql/data" not in qa_db.get("tmpfs", []):
        failures.append("qa_db no usa almacenamiento efímero")
    if "/data" not in qa_redis.get("tmpfs", []):
        failures.append("qa_redis no usa almacenamiento efímero")
    for service_name, service in (("qa_db", qa_db), ("qa_redis", qa_redis)):
        if "qa_internal" not in service.get("networks", []):
            failures.append(f"{service_name} no usa la red QA interna")
        if service.get("ports"):
            failures.append(f"{service_name} publica puertos en el host")
    qa_network = qa.get("networks", {}).get("qa_internal", {})
    if not qa_network.get("internal"):
        failures.append("La red qa_internal no está marcada como interna")

    qa_dockerfile = (root / "docker/qa/Dockerfile").read_text(encoding="utf-8")
    for token in (
        "FROM mcr.microsoft.com/playwright:v1.60.0-noble",
        "FROM python:3.12-slim-bookworm@sha256:",
        "FROM mcr.microsoft.com/playwright:v1.60.0-noble@sha256:",
        "postgresql-client-16",
        "USER vinovaqa",
        "/tmp/vinova-qa-runtime",
        "/tmp/vinova-qa-cache/ruff",
        "QA Playwright browsers OK",
    ):
        if token not in qa_dockerfile:
            failures.append(f"Dockerfile QA no contiene {token}")

    dockerignore = (root / ".dockerignore").read_text(encoding="utf-8")
    if "!.env.production.example" not in dockerignore:
        failures.append(".dockerignore excluye .env.production.example del contexto QA")
    for excluded_path in ("web_carros", "docker/nginx/certs/*"):
        if excluded_path not in dockerignore.splitlines():
            failures.append(f".dockerignore no excluye {excluded_path} del contexto de imagen")
    if "!docker/nginx/certs/.gitkeep" not in dockerignore.splitlines():
        failures.append(".dockerignore no conserva el marcador seguro del directorio TLS")

    trivy_digest = "aquasec/trivy:0.76.0@sha256:2416d1f74045b57274df1a340eee6b510cacd73c66a6ccb8da092b117eb7d222"
    for script_path in ("scripts/validate-nginx-security.ps1", "scripts/validate-nginx-security.sh"):
        script = (root / script_path).read_text(encoding="utf-8")
        if trivy_digest not in script:
            failures.append(f"{script_path} no fija Trivy por versión y digest")

    nginx_volumes = production.get("services", {}).get("nginx", {}).get("volumes", [])
    if any("/app/private" in str(volume) for volume in nginx_volumes):
        failures.append("Nginx monta almacenamiento private")

    nginx_dockerfile = (root / "docker/nginx/Dockerfile").read_text(encoding="utf-8")
    for token in (
        "FROM ghcr.io/nginx/nginx-unprivileged:1.30.4-alpine3.24@sha256:adf5042a17f4ecdd200c595fa9ffd1be37efb18f89a830bd1a00e4ab4d59d42c",
        "libexpat=2.8.5-r0",
        "pcre2=10.49-r0",
        "tiff=4.7.2-r0",
        "zlib=1.3.2-r1",
    ):
        if token not in nginx_dockerfile:
            failures.append(f"Dockerfile Nginx no contiene {token}")

    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    for token in (
        "FROM python:3.12-slim-bookworm@sha256:",
        "ARG REQUIREMENTS_FILE=production.lock",
        "pip wheel --require-hashes",
        "postgresql-client-16",
        "USER vinova",
    ):
        if token not in dockerfile:
            failures.append(f"Dockerfile no contiene {token}")

    for nginx_template in ("docker/nginx/templates/http.conf.template", "docker/nginx/templates/https.conf.template"):
        text = (root / nginx_template).read_text(encoding="utf-8")
        if "location ^~ /private/ { return 404; }" not in text:
            failures.append(f"{nginx_template} no bloquea /private/")

    if failures:
        return [_error("docker.configuration", "Configuración Docker/Nginx inconsistente: " + "; ".join(failures))]
    return [_ok("docker.configuration", "Compose, Dockerfile y Nginx conservan los controles operativos requeridos.")]


def check_release_files() -> list[ReleaseCheckResult]:
    root = Path(settings.BASE_DIR)
    missing = sorted(filename for filename in REQUIRED_RELEASE_FILES if not (root / filename).is_file())
    if missing:
        return [_error("release.files", f"Faltan archivos de release: {missing}")]
    return [_ok("release.files", f"{len(REQUIRED_RELEASE_FILES)} archivos de entrega requeridos están presentes.")]


def check_storage_layout() -> list[ReleaseCheckResult]:
    """ES: Ejecuta la operación «check storage layout» dentro del dominio de infraestructura compartida.

    EN: Executes the «check storage layout» operation within the common domain.
    """

    failures: list[str] = []
    private_root = Path(settings.PRIVATE_STORAGE_ROOT).resolve()
    public_roots = {Path(settings.MEDIA_ROOT).resolve(), Path(settings.STATIC_ROOT).resolve()}
    overlaps = [
        root
        for root in public_roots
        if private_root == root or root in private_root.parents or private_root in root.parents
    ]
    if overlaps:
        failures.append(f"PRIVATE_STORAGE_ROOT se solapa con rutas públicas: {overlaps}")

    avatar_backend = settings.STORAGE_BACKEND
    if avatar_backend not in {"local", "cloudinary"}:
        failures.append("STORAGE_BACKEND debe ser local o cloudinary")
    elif avatar_backend == "cloudinary":
        required = {
            "CLOUDINARY_CLOUD_NAME": settings.CLOUDINARY_CLOUD_NAME,
            "CLOUDINARY_API_KEY": settings.CLOUDINARY_API_KEY,
            "CLOUDINARY_API_SECRET": settings.CLOUDINARY_API_SECRET,
        }
        missing = sorted(name for name, value in required.items() if not value)
        if missing:
            failures.append(f"Cloudinary no tiene variables requeridas: {', '.join(missing)}")

    private_backend = settings.PRIVATE_STORAGE_BACKEND
    if private_backend not in {"local", "s3"}:
        failures.append("PRIVATE_STORAGE_BACKEND debe ser local o s3")
    elif private_backend == "s3":
        required = {
            "S3_ENDPOINT_URL": settings.S3_ENDPOINT_URL,
            "S3_ACCESS_KEY_ID": settings.S3_ACCESS_KEY_ID,
            "S3_SECRET_ACCESS_KEY": settings.S3_SECRET_ACCESS_KEY,
            "S3_BUCKET_NAME": settings.S3_BUCKET_NAME,
        }
        missing = sorted(name for name, value in required.items() if not value)
        if missing:
            failures.append(f"S3 privado no tiene variables requeridas: {', '.join(missing)}")
        if settings.S3_SIGNED_URL_EXPIRE_SECONDS < 1:
            failures.append("S3_SIGNED_URL_EXPIRE_SECONDS debe ser positivo")
        if settings.S3_ADDRESSING_STYLE not in {"path", "virtual", "auto"}:
            failures.append("S3_ADDRESSING_STYLE debe ser path, virtual o auto")

    if failures:
        return [_error("storage.private", "Configuración de storage inválida: " + "; ".join(failures))]
    return [_ok("storage.private", "Backends válidos y almacenamiento privado separado de rutas públicas.")]


def run_static_release_checks() -> list[ReleaseCheckResult]:
    results: list[ReleaseCheckResult] = []
    for check in (
        check_critical_routes,
        check_template_routes,
        check_template_script_policy,
        check_version_consistency,
        check_celery_configuration,
        check_docker_configuration,
        check_release_files,
        check_storage_layout,
    ):
        try:
            results.extend(check())
        except Exception as exc:  # noqa: BLE001 - release command must report the failing check
            results.append(_error(check.__name__, f"{exc.__class__.__name__}: {exc}"))
    if not results:
        results.append(_warning("release.empty", "No se ejecutaron verificaciones."))
    return results
