"""ES: Este módulo implementa el componente runner para el dominio de calidad.

EN: This module implements the runner component for the quality domain.

Contexto existente / Existing context:
Runner support for the quality domain.
"""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
import zipfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse, urlunparse

import psycopg
from django.conf import settings

PROFILE_ORDER = {"quick": 1, "full": 2, "release": 3}
VALID_PROFILES = frozenset(PROFILE_ORDER)
SENSITIVE_NAME_PATTERN = re.compile(
    r"(password|secret|token|private[_-]?key|certificate|authorization|pepper|database[_-]?url|dsn|access[_-]?key|credential)",
    re.I,
)
OUTPUT_LIMIT = 20_000


@dataclass(frozen=True)
class QualityStep:
    code: str
    category: str
    title: str
    minimum_profile: str
    command: tuple[str, ...]
    timeout_seconds: int
    required_tool: str = ""
    release_required: bool = True


@dataclass
class QualityStepResult:
    code: str
    category: str
    title: str
    status: str
    duration_seconds: float
    command: list[str]
    message: str
    output: str
    return_code: int | None


class IsolatedPostgresDatabase:
    def __init__(self, *, admin_url: str, allowed_hosts: set[str], keep: bool = False):
        self.admin_url = admin_url
        self.allowed_hosts = allowed_hosts
        self.keep = keep
        self.database_name = f"vinova_qa_{uuid.uuid4().hex[:12]}"
        self.test_url = ""

    def _validated(self):
        parsed = urlparse(self.admin_url)
        if parsed.scheme not in {"postgres", "postgresql"}:
            raise RuntimeError("VINOVA_QA_DATABASE_ADMIN_URL debe ser PostgreSQL.")
        host = (parsed.hostname or "").lower()
        if host not in self.allowed_hosts:
            raise RuntimeError(f"Host PostgreSQL QA no autorizado: {host!r}.")
        if not re.fullmatch(r"vinova_qa_[a-f0-9]{12}", self.database_name):
            raise RuntimeError("Nombre de base QA inválido.")
        return parsed

    def __enter__(self) -> str:
        parsed = self._validated()
        admin_db = parsed.path.lstrip("/") or "postgres"
        with psycopg.connect(self.admin_url, autocommit=True) as connection:
            connection.execute(f'CREATE DATABASE "{self.database_name}"')
        self.test_url = urlunparse(parsed._replace(path=f"/{self.database_name}"))
        if not admin_db:
            raise RuntimeError("La URL administrativa debe señalar una base existente.")
        return self.test_url

    def __exit__(self, exc_type, exc, traceback):
        if self.keep:
            return False
        self._validated()
        with psycopg.connect(self.admin_url, autocommit=True) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()",
                (self.database_name,),
            )
            connection.execute(f'DROP DATABASE IF EXISTS "{self.database_name}"')
        return False


def _runtime_root(root: Path) -> Path:
    configured = os.getenv("VINOVA_QA_RUNTIME_ROOT", "").strip()
    path = Path(configured) if configured else root / "run" / "qa"
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def quality_steps(root: Path) -> tuple[QualityStep, ...]:
    """Declare the deterministic commands that make up the quality pipeline."""

    python = sys.executable
    runtime_root = _runtime_root(root)
    schema_output = str(runtime_root / "openapi.yaml")
    return (
        QualityStep("static.ruff", "Código", "Ruff", "quick", (python, "-m", "ruff", "check", "."), 300),
        QualityStep(
            "django.check",
            "Django",
            "Django check",
            "quick",
            (python, "manage.py", "check", "--settings=config.settings.test"),
            180,
        ),
        QualityStep(
            "migrations.drift",
            "Base de datos",
            "Migraciones no generadas",
            "quick",
            (python, "manage.py", "makemigrations", "--check", "--dry-run", "--settings=config.settings.test"),
            180,
        ),
        QualityStep(
            "release.readiness",
            "Release",
            "Preparación estática",
            "quick",
            (python, "manage.py", "check_release_readiness", "--strict", "--settings=config.settings.test"),
            300,
        ),
        QualityStep(
            "tests.smoke",
            "Pruebas",
            "Pruebas esenciales",
            "quick",
            (
                python,
                "-m",
                "pytest",
                "-q",
                "apps/common/tests/test_release_stabilization_v023.py",
                "apps/quality/tests/test_quality_automation_v0231.py",
                "apps/quality/tests/test_qa_writable_runtime_hotfix_v02323.py",
                "apps/quality/tests/test_playwright_runtime_hotfix_v02324.py",
            ),
            900,
        ),
        QualityStep(
            "openapi.validate",
            "API",
            "OpenAPI v1",
            "full",
            (
                python,
                "manage.py",
                "spectacular",
                "--urlconf",
                "apps.api.schema_urls",
                "--validate",
                "--file",
                schema_output,
                "--settings=config.settings.test",
            ),
            300,
        ),
        QualityStep(
            "tests.full",
            "Pruebas",
            "Pytest completo",
            "full",
            (python, "-m", "pytest", "-q"),
            3600,
        ),
        QualityStep(
            "dependencies.check",
            "Dependencias",
            "Dependencias instaladas",
            "full",
            (python, "-m", "pip", "check"),
            180,
        ),
        QualityStep(
            "e2e.chromium",
            "Flujos funcionales",
            "Recorridos E2E en Chromium",
            "full",
            (python, "scripts/run_e2e.py", "--browsers", "chromium", "--output", str(runtime_root / "e2e-full")),
            2400,
        ),
        QualityStep(
            "e2e.cross_browser",
            "Flujos funcionales",
            "Recorridos E2E en Firefox y WebKit",
            "release",
            (python, "scripts/run_e2e.py", "--browsers", "firefox,webkit", "--output", str(runtime_root / "e2e-release"), "--record-video"),
            4800,
        ),
        QualityStep(
            "django.deploy",
            "Seguridad",
            "Django check --deploy",
            "release",
            (python, "manage.py", "check", "--deploy", "--settings=config.settings.production"),
            300,
        ),
        QualityStep(
            "database.migrate",
            "Base de datos",
            "Migración en PostgreSQL aislado",
            "release",
            (python, "manage.py", "migrate", "--noinput", "--settings=config.settings.test"),
            1200,
        ),
        QualityStep(
            "seeds.idempotency",
            "Datos base",
            "Seeds idempotentes",
            "release",
            (python, "manage.py", "check_seed_idempotency", "--settings=config.settings.test"),
            900,
        ),
        QualityStep(
            "database.readiness",
            "Base de datos",
            "Migraciones aplicadas",
            "release",
            (
                python,
                "manage.py",
                "check_release_readiness",
                "--database",
                "--strict",
                "--settings=config.settings.test",
            ),
            300,
        ),
        QualityStep(
            "nginx.syntax",
            "Producción",
            "Plantillas Nginx",
            "release",
            (python, "scripts/check_nginx_templates.py"),
            300,
            required_tool="nginx",
        ),
        QualityStep(
            "javascript.syntax",
            "Frontend",
            "Sintaxis JavaScript",
            "release",
            (python, "scripts/check_javascript.py"),
            300,
        ),
        QualityStep(
            "package.clean",
            "Entrega",
            "ZIP limpio y checksum",
            "release",
            (python, "scripts/check_release_package.py"),
            900,
        ),
    )


def _selected_steps(root: Path, profile: str) -> list[QualityStep]:
    if profile not in VALID_PROFILES:
        raise ValueError(f"Perfil QA no válido: {profile!r}.")
    level = PROFILE_ORDER[profile]
    return [step for step in quality_steps(root) if PROFILE_ORDER[step.minimum_profile] <= level]


def _playwright_browsers_path() -> str:
    """Return a trusted existing Playwright browser directory for QA.

    The official Playwright Docker image stores browsers in /ms-playwright.
    We intentionally do not reuse arbitrary relative paths from the host.
    """

    candidates = (
        os.environ.get("VINOVA_QA_PLAYWRIGHT_BROWSERS_PATH", "").strip(),
        os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "").strip(),
        "/ms-playwright",
    )
    for raw in candidates:
        if not raw:
            continue
        path = Path(raw)
        if path.is_absolute() and path.is_dir():
            return str(path.resolve())
    return ""


def _safe_environment(root: Path, *, profile: str, test_database_url: str = "") -> dict[str, str]:
    inherited_names = {
        "PATH",
        "HOME",
        "LANG",
        "LC_ALL",
        "TZ",
        "TMPDIR",
        "TEMP",
        "TMP",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "PATHEXT",
        "VIRTUAL_ENV",
        "PYTHONIOENCODING",
        "SSL_CERT_FILE",
        "REQUESTS_CA_BUNDLE",
        "CI",
        "NO_COLOR",
    }
    env = {name: value for name in inherited_names if (value := os.environ.get(name))}
    env.update(
        {
            "DJANGO_SETTINGS_MODULE": "config.settings.test",
            "PYTHONPATH": str(root),
            "VINOVA_QA_ACTIVE": "1",
            "SECRET_KEY": "qa-only-secret-key-not-for-production-93cf1f76-a8c41d7e5b209f64",
            "VINOVA_API_TOKEN_PEPPER": "qa-only-independent-pepper-63ef8fc6-b7d12e5a9034fc88",
            "DEBUG": "False",
            "ALLOWED_HOSTS": "localhost,127.0.0.1,testserver,qa.local",
            "CSRF_TRUSTED_ORIGINS": "https://qa.local",
            "VINOVA_WEBHOOK_ALLOW_PRIVATE_NETWORKS": "False",
            "VINOVA_BACKUP_SYNC_FALLBACK": "False",
            "VINOVA_AUTOMATED_BACKUPS_ENABLED": "False",
            "VINOVA_QA_AUTOMATED_ENABLED": "False",
            "SENTRY_DSN": "",
            "SENTRY_RELEASE": f"vinova-pro@{settings.VINOVA_PRODUCT_VERSION}",
            "VINOVA_QA_RUNTIME_ROOT": str(_runtime_root(root)),
            "RUFF_CACHE_DIR": str(_runtime_root(root) / "cache" / "ruff"),
            "XDG_CACHE_HOME": str(_runtime_root(root) / "cache"),
            "PYTEST_ADDOPTS": f"-o cache_dir={_runtime_root(root) / 'cache' / 'pytest'}",
        }
    )
    playwright_browsers_path = _playwright_browsers_path()
    if playwright_browsers_path:
        env["PLAYWRIGHT_BROWSERS_PATH"] = playwright_browsers_path
        env["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "1"

    qa_redis_url = os.getenv("VINOVA_QA_REDIS_URL", "").strip()
    if qa_redis_url:
        env["REDIS_URL"] = qa_redis_url
        env["CELERY_BROKER_URL"] = qa_redis_url
        env["CELERY_RESULT_BACKEND"] = qa_redis_url
    if test_database_url:
        env["TEST_DATABASE_URL"] = test_database_url
        env["DATABASE_URL"] = test_database_url
    if profile == "release":
        env["DJANGO_SETTINGS_MODULE"] = "config.settings.test"
    return env


def _redaction_values(env: dict[str, str]) -> list[str]:
    values = []
    for name, value in env.items():
        if value and len(value) >= 8 and SENSITIVE_NAME_PATTERN.search(name):
            values.append(value)
    return sorted(set(values), key=len, reverse=True)


def redact(text: str, *, env: dict[str, str]) -> str:
    sanitized = text
    for value in _redaction_values(env):
        sanitized = sanitized.replace(value, "[REDACTADO]")
    sanitized = re.sub(
        r"(?i)(password|secret|token|authorization|pepper)(\s*[:=]\s*)([^\s,;]+)",
        r"\1\2[REDACTADO]",
        sanitized,
    )
    return sanitized


def _command_for_display(command: Iterable[str], env: dict[str, str]) -> list[str]:
    return [redact(str(item), env=env) for item in command]


def _run_step(step: QualityStep, *, root: Path, env: dict[str, str], profile: str) -> QualityStepResult:
    if step.required_tool and shutil.which(step.required_tool) is None:
        status = "failed" if profile == "release" and step.release_required else "warning"
        return QualityStepResult(
            code=step.code,
            category=step.category,
            title=step.title,
            status=status,
            duration_seconds=0.0,
            command=_command_for_display(step.command, env),
            message=f"Herramienta requerida no disponible: {step.required_tool}.",
            output="",
            return_code=None,
        )

    started = time.monotonic()
    try:
        process = subprocess.run(
            step.command,
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=step.timeout_seconds,
            check=False,
        )
        duration = time.monotonic() - started
        output = redact((process.stdout or "") + ("\n" if process.stdout and process.stderr else "") + (process.stderr or ""), env=env)
        output = output[-OUTPUT_LIMIT:]
        passed = process.returncode == 0
        return QualityStepResult(
            code=step.code,
            category=step.category,
            title=step.title,
            status="passed" if passed else "failed",
            duration_seconds=round(duration, 3),
            command=_command_for_display(step.command, env),
            message="Control aprobado." if passed else f"El comando terminó con código {process.returncode}.",
            output=output,
            return_code=process.returncode,
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - started
        output = redact(((exc.stdout or "") + "\n" + (exc.stderr or ""))[-OUTPUT_LIMIT:], env=env)
        return QualityStepResult(
            code=step.code,
            category=step.category,
            title=step.title,
            status="failed",
            duration_seconds=round(duration, 3),
            command=_command_for_display(step.command, env),
            message=f"Tiempo máximo excedido ({step.timeout_seconds}s).",
            output=output,
            return_code=None,
        )
    except OSError as exc:
        duration = time.monotonic() - started
        return QualityStepResult(
            code=step.code,
            category=step.category,
            title=step.title,
            status="error",
            duration_seconds=round(duration, 3),
            command=_command_for_display(step.command, env),
            message=f"{exc.__class__.__name__}: {exc}",
            output="",
            return_code=None,
        )


def _git_commit(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _report_paths(report_dir: Path, run_id: str) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir / f"qa-{run_id}.json", report_dir / f"qa-{run_id}.html"


def write_reports(report: dict, *, report_dir: Path, run_id: str) -> tuple[Path, Path]:
    json_path, html_path = _report_paths(report_dir, run_id)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    rows = []
    for check in report["checks"]:
        command = " ".join(check["command"])
        rows.append(
            "<tr>"
            f"<td>{html.escape(check['category'])}</td>"
            f"<td><strong>{html.escape(check['title'])}</strong><br><code>{html.escape(check['code'])}</code></td>"
            f"<td>{html.escape(check['status'].upper())}</td>"
            f"<td>{check['duration_seconds']:.3f}s</td>"
            f"<td><details><summary>{html.escape(check['message'])}</summary>"
            f"<p><code>{html.escape(command)}</code></p><pre>{html.escape(check['output'])}</pre></details></td>"
            "</tr>"
        )
    document = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vinova QA {html.escape(run_id)}</title>
<style>body{{font-family:Arial,sans-serif;margin:2rem;color:#172033}}table{{width:100%;border-collapse:collapse}}th,td{{padding:.7rem;border:1px solid #d8e0ea;vertical-align:top}}th{{background:#eef3f8}}pre{{white-space:pre-wrap;max-height:24rem;overflow:auto;background:#f7f9fc;padding:1rem}}code{{word-break:break-all}}.summary{{display:flex;gap:1rem;flex-wrap:wrap}}.summary span{{padding:.6rem 1rem;background:#eef3f8;border-radius:.5rem}}</style>
</head><body><h1>Vinova Pro · QA {html.escape(report['profile'])}</h1>
<p>Estado: <strong>{html.escape(report['status'].upper())}</strong> · Versión {html.escape(report['source_version'])} · {html.escape(report['started_at'])}</p>
<div class="summary"><span>Aprobadas: {report['counts']['passed']}</span><span>Advertencias: {report['counts']['warning']}</span><span>Fallidas: {report['counts']['failed']}</span><span>Omitidas: {report['counts']['skipped']}</span></div>
<table><thead><tr><th>Categoría</th><th>Control</th><th>Estado</th><th>Duración</th><th>Evidencia</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
</body></html>"""
    html_path.write_text(document, encoding="utf-8")
    return json_path, html_path


def _collect_e2e_evidence(root: Path, report_dir: Path, run_id: str) -> tuple[dict, str]:
    summaries = []
    evidence_dirs = []
    runtime_root = _runtime_root(root)
    for name in ("e2e-full", "e2e-release"):
        directory = runtime_root / name
        summary_path = directory / "summary.json"
        if summary_path.is_file():
            try:
                summaries.append(json.loads(summary_path.read_text(encoding="utf-8")))
                evidence_dirs.append(directory)
            except (OSError, json.JSONDecodeError):
                continue
    if not summaries:
        return {}, ""

    matrix: dict[str, dict[str, int]] = {}
    browsers = []
    counts = {"passed": 0, "failed": 0, "skipped": 0}
    for summary in summaries:
        browsers.extend(summary.get("browsers") or [])
        for key in counts:
            counts[key] += int((summary.get("counts") or {}).get(key) or 0)
        for module, row in (summary.get("module_matrix") or {}).items():
            target = matrix.setdefault(module, {"passed": 0, "failed": 0, "error": 0, "skipped": 0, "total": 0})
            for key in target:
                target[key] += int(row.get(key) or 0)

    archive_name = f"qa-{run_id}-e2e-evidence.zip"
    archive_path = report_dir / archive_name
    report_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for directory in evidence_dirs:
            for path in directory.rglob("*"):
                if path.is_file():
                    archive.write(path, arcname=(Path("e2e") / path.relative_to(runtime_root)).as_posix())
    return {
        "status": "passed" if counts["failed"] == 0 else "failed",
        "browsers": sorted(set(browsers)),
        "counts": counts,
        "module_matrix": dict(sorted(matrix.items())),
    }, archive_name


def run_quality_profile(
    *,
    profile: str,
    root: Path,
    report_dir: Path,
    run_id: str | None = None,
    require_postgres: bool | None = None,
) -> dict:
    """Run a named quality profile and persist its machine-readable report."""

    root = root.resolve()
    report_dir = report_dir.resolve()
    runtime_root = _runtime_root(root)
    runtime_root.mkdir(parents=True, exist_ok=True)
    (runtime_root / "cache" / "ruff").mkdir(parents=True, exist_ok=True)
    (runtime_root / "cache" / "pytest").mkdir(parents=True, exist_ok=True)
    run_id = run_id or uuid.uuid4().hex
    if profile not in VALID_PROFILES:
        raise ValueError(f"Perfil QA no válido: {profile!r}.")

    if require_postgres is None:
        require_postgres = profile == "release"
    admin_url = os.getenv("VINOVA_QA_DATABASE_ADMIN_URL", "").strip()
    allowed_hosts = {
        item.strip().lower()
        for item in os.getenv("VINOVA_QA_ALLOWED_DB_HOSTS", "qa_db,localhost,127.0.0.1").split(",")
        if item.strip()
    }
    keep_database = os.getenv("VINOVA_QA_KEEP_DATABASE", "False").lower() in {"1", "true", "yes"}

    database_context = None
    test_database_url = ""
    if admin_url:
        database_context = IsolatedPostgresDatabase(
            admin_url=admin_url,
            allowed_hosts=allowed_hosts,
            keep=keep_database,
        )
        test_database_url = database_context.__enter__()
    elif require_postgres:
        raise RuntimeError(
            "El perfil release exige PostgreSQL aislado. Configure VINOVA_QA_DATABASE_ADMIN_URL o use el contenedor QA."
        )

    started_at = datetime.now(UTC)
    started = time.monotonic()
    env = _safe_environment(root, profile=profile, test_database_url=test_database_url)
    results: list[QualityStepResult] = []
    try:
        for step in _selected_steps(root, profile):
            result = _run_step(step, root=root, env=env, profile=profile)
            results.append(result)
            if result.status in {"failed", "error"} and os.getenv("VINOVA_QA_FAIL_FAST", "False").lower() in {
                "1",
                "true",
                "yes",
            }:
                break
    finally:
        if database_context is not None:
            database_context.__exit__(None, None, None)

    counts = {
        "passed": sum(item.status == "passed" for item in results),
        "warning": sum(item.status == "warning" for item in results),
        "failed": sum(item.status in {"failed", "error"} for item in results),
        "skipped": sum(item.status == "skipped" for item in results),
    }
    status = "passed" if counts["failed"] == 0 else "failed"
    completed_at = datetime.now(UTC)
    e2e_summary, e2e_artifact_path = _collect_e2e_evidence(root, report_dir, run_id)
    e2e_release_complete = set(e2e_summary.get("browsers") or []) >= {"chromium", "firefox", "webkit"}
    report = {
        "schema_version": 1,
        "run_id": run_id,
        "profile": profile,
        "status": status,
        "release_ready": (
            profile == "release"
            and status == "passed"
            and counts["warning"] == 0
            and bool(test_database_url)
            and e2e_release_complete
            and e2e_summary.get("status") == "passed"
        ),
        "source_version": settings.VINOVA_PRODUCT_VERSION,
        "source_commit": _git_commit(root),
        "environment": os.getenv("VINOVA_QA_ENVIRONMENT", "qa-isolated"),
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "duration_seconds": round(time.monotonic() - started, 3),
        "counts": counts,
        "database": {
            "engine": "postgresql" if test_database_url else "sqlite",
            "isolated": bool(test_database_url),
            "retained": bool(test_database_url and keep_database),
        },
        "functional_e2e": e2e_summary,
        "e2e_artifact_path": e2e_artifact_path,
        "checks": [asdict(item) for item in results],
    }
    json_path, html_path = write_reports(report, report_dir=report_dir, run_id=run_id)
    report["report_json_path"] = json_path.relative_to(report_dir).as_posix()
    report["report_html_path"] = html_path.relative_to(report_dir).as_posix()
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
