#!/usr/bin/env python3
"""ES: Este módulo implementa el componente run deployment smoke para el dominio de operación y QA.

EN: This module implements the run deployment smoke component for the operations and QA domain.

Contexto existente / Existing context:
Operational script for run deployment smoke.
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.deployment_smoke import test_accessibility, test_assets, test_auth, test_cleanup, test_demo  # noqa: E402
from tests.deployment_smoke import test_health, test_private_navigation, test_public, test_roles, test_security, test_tls  # noqa: E402
from tests.deployment_smoke import test_write_flows  # noqa: E402
from tests.deployment_smoke.helpers.browser import BrowserDependencyError, BrowserSession  # noqa: E402
from tests.deployment_smoke.helpers.evidence import finalize_reports  # noqa: E402
from tests.deployment_smoke.helpers.models import CheckResult, RunState, SmokeConfig  # noqa: E402
from tests.deployment_smoke.helpers.security import redact, validate_target_url  # noqa: E402

MODES = {"production", "staging", "demo"}
SCENARIOS = {
    "public",
    "tls",
    "assets",
    "health",
    "auth",
    "navigation",
    "security",
    "roles",
    "customers",
    "vehicles",
    "inventory",
    "sales",
    "documents",
    "accessibility",
    "cleanup",
    "demo",
    "all",
}
ORDER = [
    "tls",
    "public",
    "auth",
    "health",
    "assets",
    "navigation",
    "security",
    "roles",
    "customers",
    "vehicles",
    "inventory",
    "sales",
    "documents",
    "accessibility",
    "demo",
    "cleanup",
]
MODE_DEFAULTS = {
    "production": ["tls", "public", "auth", "health", "assets", "navigation", "security", "roles", "accessibility"],
    "staging": [
        "tls",
        "public",
        "auth",
        "health",
        "assets",
        "navigation",
        "security",
        "roles",
        "customers",
        "vehicles",
        "inventory",
        "sales",
        "documents",
        "accessibility",
        "cleanup",
    ],
    "demo": [
        "tls",
        "public",
        "auth",
        "health",
        "navigation",
        "customers",
        "vehicles",
        "inventory",
        "sales",
        "documents",
        "security",
        "roles",
        "accessibility",
        "demo",
        "cleanup",
    ],
}
BROWSER_SCENARIOS = SCENARIOS - {"tls", "all"}
AUTH_SCENARIOS = {
    "auth",
    "assets",
    "navigation",
    "security",
    "customers",
    "vehicles",
    "inventory",
    "sales",
    "documents",
    "accessibility",
    "cleanup",
    "demo",
}


class ConfigurationError(ValueError):
    """Configuración válida sintácticamente, pero incompleta o insegura."""


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(message)


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def build_parser() -> SafeArgumentParser:
    parser = SafeArgumentParser(description="Vinova Deployment Smoke Bot para instalaciones externas.")
    parser.add_argument("base_url", nargs="?", default=os.getenv("VINOVA_SMOKE_BASE_URL", ""))
    parser.add_argument("--mode", choices=sorted(MODES), default=os.getenv("VINOVA_SMOKE_MODE", "production"))
    parser.add_argument("--scenario", action="append", default=[], help="Nombre cerrado; puede repetirse. No usar comas.")
    parser.add_argument("--username", default=os.getenv("VINOVA_SMOKE_USERNAME", ""))
    parser.add_argument("--password", default=os.getenv("VINOVA_SMOKE_PASSWORD", ""))
    parser.add_argument("--browser", choices=["chromium", "firefox", "webkit"], default="chromium")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout", type=int, default=int(os.getenv("VINOVA_SMOKE_TIMEOUT", "30")))
    parser.add_argument("--retries", type=int, default=int(os.getenv("VINOVA_SMOKE_RETRIES", "1")))
    parser.add_argument("--report-dir", type=Path, default=Path(os.getenv("VINOVA_SMOKE_REPORT_DIR", "private/qa_reports")))
    parser.add_argument("--write-tests", action="store_true")
    parser.add_argument("--cleanup", action="store_true")
    parser.add_argument("--record-video", action="store_true")
    parser.add_argument("--retain-demo-data", action="store_true")
    parser.add_argument("--confirm-retain-demo-data", default=os.getenv("VINOVA_SMOKE_RETAIN_CONFIRM", ""))
    parser.add_argument("--confirm-demo-target", default=os.getenv("VINOVA_SMOKE_DEMO_CONFIRM", ""))
    parser.add_argument("--allow-http-local", action="store_true")
    parser.add_argument("--insecure-local-tls", action="store_true")
    parser.add_argument("--role-credentials-file", type=Path, default=os.getenv("VINOVA_SMOKE_ROLE_CREDENTIALS_FILE"))
    return parser


def normalize_scenarios(raw: list[str], mode: str) -> list[str]:
    """ES: Ejecuta la operación «normalize scenarios» dentro del dominio de operación y QA.

    EN: Executes the «normalize scenarios» operation within the operations and QA domain.
    """

    requested = raw or ["all"]
    if any("," in item for item in requested):
        raise ValueError("No uses listas con comas. Repite --scenario para varios escenarios.")
    invalid = sorted(set(requested) - SCENARIOS)
    if invalid:
        raise ValueError(f"Escenarios no permitidos: {', '.join(invalid)}.")
    if "all" in requested and len(requested) > 1:
        raise ValueError("Usa --scenario all solo, o varios --scenario sin all.")
    selected = MODE_DEFAULTS[mode] if requested == ["all"] else list(dict.fromkeys(requested))
    if any(item in AUTH_SCENARIOS - {"auth"} for item in selected) and "auth" not in selected:
        selected.insert(0, "auth")
    return [item for item in ORDER if item in selected]


def validate_config(args: argparse.Namespace) -> SmokeConfig:
    """Normalize CLI input and reject unsafe deployment-smoke targets."""

    base_url = validate_target_url(args.base_url, allow_http_local=args.allow_http_local)
    scenarios = normalize_scenarios(args.scenario, args.mode)
    if args.timeout < 1 or args.timeout > 600:
        raise ValueError("--timeout debe estar entre 1 y 600 segundos.")
    if args.retries < 0 or args.retries > 5:
        raise ValueError("--retries debe estar entre 0 y 5.")
    write_selected = any(item in test_write_flows.WRITE_SCENARIOS for item in scenarios)
    effective_write = write_selected and (args.write_tests or args.mode == "demo")
    effective_cleanup = args.cleanup or "cleanup" in scenarios
    allow_write = env_bool("VINOVA_SMOKE_ALLOW_WRITE")
    if args.mode == "production" and (effective_write or write_selected or args.retain_demo_data):
        raise ConfigurationError("Producción prohíbe escrituras, demo y retención de datos.")
    if args.mode == "staging" and write_selected and not args.write_tests:
        raise ConfigurationError("Staging con escritura requiere --write-tests.")
    if args.mode in {"staging", "demo"} and write_selected and not allow_write:
        raise ConfigurationError("Las escrituras requieren VINOVA_SMOKE_ALLOW_WRITE=true en el entorno del runner.")
    if args.mode == "staging" and write_selected and not args.cleanup:
        raise ConfigurationError("Staging con escritura requiere --cleanup.")
    hostname = base_url.split("//", 1)[-1].split("/", 1)[0].split(":", 1)[0].lower()
    if args.insecure_local_tls:
        if args.mode == "production":
            raise ConfigurationError("Producción prohíbe --insecure-local-tls.")
        if hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ConfigurationError("--insecure-local-tls solo se permite para localhost.")
    if args.mode == "demo" and args.confirm_demo_target.strip().lower() != hostname:
        raise ConfigurationError("Demo requiere --confirm-demo-target con el hostname exacto no productivo.")
    if args.retain_demo_data:
        expected = f"RETAIN-{hostname}"
        if args.mode != "demo" or args.confirm_retain_demo_data != expected:
            raise ConfigurationError(f"--retain-demo-data requiere --confirm-retain-demo-data {expected!r}.")
    if any(item in AUTH_SCENARIOS for item in scenarios) and (not args.username or not args.password):
        raise PermissionError("Faltan VINOVA_SMOKE_USERNAME y VINOVA_SMOKE_PASSWORD.")
    role_credentials_file = Path(args.role_credentials_file).resolve() if args.role_credentials_file else None
    if "roles" in scenarios and (role_credentials_file is None or not role_credentials_file.is_file()):
        raise ConfigurationError("El escenario roles requiere --role-credentials-file con un manifest existente.")
    report_root = args.report_dir if args.report_dir.is_absolute() else (ROOT / args.report_dir)
    return SmokeConfig(
        base_url=base_url,
        mode=args.mode,
        scenarios=scenarios,
        username=args.username,
        password=args.password,
        browser=args.browser,
        headless=not args.headed,
        timeout_seconds=args.timeout,
        retries=args.retries,
        report_root=report_root.resolve(),
        write_tests=effective_write,
        cleanup=effective_cleanup,
        retain_demo_data=args.retain_demo_data,
        record_video=args.record_video,
        allow_http_local=args.allow_http_local,
        verify_tls=not args.insecure_local_tls,
        demo_confirmation=args.confirm_demo_target,
        retain_confirmation=args.confirm_retain_demo_data,
        role_credentials_file=role_credentials_file,
    )


def failure_state(*, message: str, exit_code: int, base_url: str = "", mode: str = "production") -> RunState:
    run_id = uuid.uuid4().hex[:12]
    root = Path(os.getenv("VINOVA_SMOKE_REPORT_DIR", "private/qa_reports"))
    if not root.is_absolute():
        root = ROOT / root
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    config = SmokeConfig(
        base_url=base_url or "invalid://target",
        mode=mode if mode in MODES else "production",
        scenarios=[],
        report_root=root,
        run_id=run_id,
    )
    state = RunState(config=config, output_dir=root / f"deployment-smoke-{timestamp}-{run_id}", exit_code=exit_code)
    state.add(
        CheckResult(
            code="runner.configuration",
            scenario="runner",
            title="Configuración del bot",
            status="failed",
            message=redact(message),
        )
    )
    return state


def scenario_runner(name: str, state: RunState, session: BrowserSession | None) -> None:
    mapping = {
        "tls": test_tls.run,
        "public": test_public.run,
        "auth": test_auth.run,
        "health": test_health.run,
        "assets": test_assets.run,
        "navigation": test_private_navigation.run,
        "security": test_security.run,
        "roles": test_roles.run,
        "accessibility": test_accessibility.run,
        "demo": test_demo.run,
        "cleanup": test_cleanup.run,
    }
    if name in test_write_flows.WRITE_SCENARIOS:
        test_write_flows.run_scenario(state, session, name)
    else:
        mapping[name](state, session)


def main(argv: list[str] | None = None) -> int:
    """Execute the requested deployment smoke scenarios and summarize results."""

    raw = sys.argv[1:] if argv is None else argv
    try:
        args = build_parser().parse_args(raw)
        config = validate_config(args)
    except PermissionError as exc:
        state = failure_state(message=str(exc), exit_code=4, base_url=getattr(locals().get("args", None), "base_url", ""), mode=getattr(locals().get("args", None), "mode", "production"))
        paths = finalize_reports(state)
        print(f"Resumen: {paths['summary']}")
        return 4
    except ConfigurationError as exc:
        state = failure_state(message=str(exc), exit_code=3, base_url=getattr(locals().get("args", None), "base_url", ""), mode=getattr(locals().get("args", None), "mode", "production"))
        paths = finalize_reports(state)
        print(f"Resumen: {paths['summary']}")
        return 3
    except (ValueError, TypeError) as exc:
        state = failure_state(message=str(exc), exit_code=2, base_url=getattr(locals().get("args", None), "base_url", ""), mode=getattr(locals().get("args", None), "mode", "production"))
        paths = finalize_reports(state)
        print(f"Resumen: {paths['summary']}")
        return 2

    output_dir = config.report_dir
    state = RunState(config=config, output_dir=output_dir)
    session: BrowserSession | None = None
    needs_browser = any(item in BROWSER_SCENARIOS for item in config.scenarios)
    try:
        if needs_browser:
            session = BrowserSession(
                base_url=config.base_url,
                browser_name=config.browser,
                timeout_seconds=config.timeout_seconds,
                headless=config.headless,
                output_dir=output_dir,
                record_video=config.record_video,
                verify_tls=config.verify_tls,
            )
            session.__enter__()
        for scenario in config.scenarios:
            if scenario == "cleanup":
                continue
            scenario_runner(scenario, state, session)
        if config.cleanup or "cleanup" in config.scenarios:
            scenario_runner("cleanup", state, session)
        if session is not None and "auth" in config.scenarios:
            try:
                session.logout()
                state.add(
                    CheckResult(
                        code="auth.logout",
                        scenario="auth",
                        title="Cierre de sesión",
                        status="passed",
                        message="Sesión cerrada correctamente.",
                    )
                )
            except Exception as exc:  # noqa: BLE001
                state.add(
                    CheckResult(
                        code="auth.logout",
                        scenario="auth",
                        title="Cierre de sesión",
                        status="failed",
                        message=redact(f"{type(exc).__name__}: {exc}", [config.password]),
                    )
                )
    except BrowserDependencyError as exc:
        state.exit_code = 3
        state.add(
            CheckResult(
                code="runner.dependencies",
                scenario="runner",
                title="Dependencias del navegador",
                status="failed",
                message=redact(str(exc), [config.password]),
            )
        )
    except Exception as exc:  # noqa: BLE001
        state.add(
            CheckResult(
                code="runner.unhandled",
                scenario="runner",
                title="Ejecución del bot",
                status="failed",
                message=redact(f"{type(exc).__name__}: {exc}", [config.password]),
                details={"traceback": redact(traceback.format_exc(limit=8), [config.password])},
            )
        )
        if config.cleanup and session is not None and state.resources:
            try:
                test_cleanup.run(state, session)
            except Exception as cleanup_exc:  # noqa: BLE001
                state.exit_code = 6
                state.add(
                    CheckResult(
                        code="cleanup.emergency",
                        scenario="cleanup",
                        title="Limpieza tras fallo",
                        status="failed",
                        message=redact(f"{type(cleanup_exc).__name__}: {cleanup_exc}", [config.password]),
                    )
                )
    finally:
        if session is not None:
            session.__exit__(None, None, None)

    if state.exit_code not in {3, 6}:
        network_failure = any(check.code == "network.dns" and check.status == "failed" for check in state.checks)
        state.exit_code = 5 if network_failure else (0 if state.deployment_ready() else 1)
    paths = finalize_reports(state)
    print(f"Deployment smoke: {state.status()} · aprobadas={state.counts()['passed']} · advertencias={state.counts()['warning']} · fallidas={state.counts()['failed']} · omitidas={state.counts()['skipped']}")
    print(f"JSON: {paths['summary']}")
    print(f"HTML: {paths['html']}")
    print(f"JUnit: {paths['junit']}")
    print(f"Evidencia: {paths['evidence']}")
    return state.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
