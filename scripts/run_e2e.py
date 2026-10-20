#!/usr/bin/env python3
"""ES: Este módulo implementa el componente run e2e para el dominio de operación y QA.

EN: This module implements the run e2e component for the operations and QA domain.

Contexto existente / Existing context:
Operational script for run e2e.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from playwright.sync_api import sync_playwright

SCENARIOS = {
    "public": ("tests/e2e/test_01_public.py", "Público y solicitudes"),
    "auth": ("tests/e2e/test_02_auth.py", "Autenticación y navegación"),
    "vehicles": ("tests/e2e/test_03_vehicles.py", "Vehículos"),
    "customers": ("tests/e2e/test_04_customers.py", "Clientes"),
    "inventory": ("tests/e2e/test_05_inventory.py", "Inventario"),
    "sales": ("tests/e2e/test_06_sales.py", "CRM, ventas y facturación"),
    "documents": ("tests/e2e/test_07_documents.py", "Documentos, reportes e importaciones"),
    "security": ("tests/e2e/test_08_security.py", "Privacidad, seguridad y continuidad"),
    "roles": ("tests/e2e/test_09_roles.py", "Roles y permisos"),
    "accessibility": ("tests/e2e/test_10_accessibility.py", "Responsive y accesibilidad"),
    "portal": ("tests/e2e/test_11_portal.py", "Portal del cliente"),
    "maps": ("tests/e2e/test_12_functional_maps.py", "Mapas funcionales"),
}

LEGACY_ALIASES = {
    "test_01": "public",
    "test_02": "auth",
    "test_03": "vehicles",
    "test_04": "customers",
    "test_05": "inventory",
    "test_06": "sales",
    "test_07": "documents",
    "test_08": "security",
    "test_09": "roles",
    "test_10": "accessibility",
    "test_11": "portal",
    "test_12": "maps",
}

MODULE_BY_TEST_PREFIX = {
    "test_portal": SCENARIOS["portal"][1],
    "test_01": SCENARIOS["public"][1],
    "test_02": SCENARIOS["auth"][1],
    "test_03": SCENARIOS["vehicles"][1],
    "test_04": SCENARIOS["customers"][1],
    "test_05": SCENARIOS["inventory"][1],
    "test_06": SCENARIOS["sales"][1],
    "test_07": SCENARIOS["documents"][1],
    "test_08": SCENARIOS["security"][1],
    "test_09": SCENARIOS["roles"][1],
    "test_10": SCENARIOS["accessibility"][1],
    "test_12": SCENARIOS["maps"][1],
}


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(message)


def module_for(name: str) -> str:
    return next((module for prefix, module in MODULE_BY_TEST_PREFIX.items() if name.startswith(prefix)), "Otros")


def parse_junit(path: Path, browser: str) -> list[dict]:
    if not path.exists():
        return [
            {
                "browser": browser,
                "module": "Infraestructura E2E",
                "test": "junit",
                "status": "error",
                "message": "No se generó JUnit XML.",
            }
        ]
    root = ET.parse(path).getroot()
    results = []
    for case in root.iter("testcase"):
        name = case.attrib.get("name", "sin_nombre")
        status = "passed"
        message = ""
        if case.find("failure") is not None:
            status = "failed"
            message = (case.find("failure").attrib.get("message") or "")[:500]
        elif case.find("error") is not None:
            status = "error"
            message = (case.find("error").attrib.get("message") or "")[:500]
        elif case.find("skipped") is not None:
            status = "skipped"
            message = (case.find("skipped").attrib.get("message") or "")[:500]
        results.append(
            {
                "browser": browser,
                "module": module_for(name),
                "test": name,
                "status": status,
                "duration_seconds": float(case.attrib.get("time", 0) or 0),
                "message": message,
            }
        )
    return results


def browser_preflight(browsers: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    resolved: dict[str, str] = {}
    missing: dict[str, str] = {}
    try:
        with sync_playwright() as playwright:
            for browser in browsers:
                explicit = os.getenv(f"VINOVA_E2E_{browser.upper()}_EXECUTABLE_PATH", "").strip()
                if not explicit and len(browsers) == 1:
                    explicit = os.getenv("VINOVA_E2E_EXECUTABLE_PATH", "").strip()
                executable = Path(explicit) if explicit else Path(getattr(playwright, browser).executable_path)
                if executable.is_file():
                    resolved[browser] = str(executable.resolve())
                else:
                    missing[browser] = str(executable)
    except Exception as exc:  # pragma: no cover - defensive infrastructure guard
        missing["playwright"] = f"{type(exc).__name__}: {exc}"
    return resolved, missing


def resolve_output(root: Path, value: str) -> Path:
    requested = Path(value)
    return requested.resolve() if requested.is_absolute() else (root / requested).resolve()


def output_from_raw_args(root: Path, argv: list[str]) -> Path:
    default = "run/qa/e2e"
    for index, token in enumerate(argv):
        if token == "--output" and index + 1 < len(argv):
            return resolve_output(root, argv[index + 1])
        if token.startswith("--output="):
            return resolve_output(root, token.split("=", 1)[1])
    return resolve_output(root, default)


def write_summary(output: Path, payload: dict) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def failure_summary(
    output: Path,
    *,
    message: str,
    phase: str,
    browsers: list[str] | None = None,
    selected_scenarios: list[str] | None = None,
    started: float | None = None,
    exit_code: int = 1,
) -> int:
    browsers = browsers or []
    selected_scenarios = selected_scenarios or []
    result = {
        "browser": browsers[0] if browsers else "",
        "module": "Infraestructura E2E",
        "test": phase,
        "status": "error",
        "duration_seconds": 0.0,
        "message": message,
    }
    payload = {
        "schema_version": 1,
        "status": "failed",
        "phase": phase,
        "browsers": browsers,
        "selected_scenarios": selected_scenarios,
        "duration_seconds": round(time.monotonic() - started, 3) if started is not None else 0.0,
        "counts": {"passed": 0, "failed": 1, "skipped": 0},
        "module_matrix": {
            "Infraestructura E2E": {"passed": 0, "failed": 0, "error": 1, "skipped": 0, "total": 1}
        },
        "results": [result],
        "commands": [],
        "exit_code": exit_code,
    }
    write_summary(output, payload)
    print(message, file=sys.stderr)
    print(f"Resumen: {output / 'summary.json'}")
    return exit_code


def normalize_scenarios(positional: list[str], legacy_value: str) -> list[str]:
    raw = list(positional)
    if legacy_value:
        if raw:
            raise ValueError("No combines escenarios posicionales con --tests.")
        raw = [item.strip() for item in legacy_value.split(",") if item.strip()]
    if not raw:
        raw = ["all"]

    normalized = [LEGACY_ALIASES.get(item.lower(), item.lower()) for item in raw]
    if "all" in normalized and len(normalized) > 1:
        raise ValueError("Usa 'all' solo o varios nombres de escenario sin comas.")
    if normalized == ["all"]:
        return list(SCENARIOS)

    invalid = sorted(set(normalized) - set(SCENARIOS))
    if invalid:
        allowed = ", ".join([*SCENARIOS, "all"])
        raise ValueError(f"Escenarios E2E no permitidos: {', '.join(invalid)}. Usa: {allowed}.")
    return list(dict.fromkeys(normalized))


def build_parser() -> SafeArgumentParser:
    parser = SafeArgumentParser(description="Ejecuta recorridos E2E aislados de Vinova Pro.")
    parser.add_argument("scenarios", nargs="*", help="Nombres cerrados: public, auth, ..., accessibility, maps o all")
    parser.add_argument("--browsers", default="chromium", help="chromium, firefox, webkit o lista por comas")
    parser.add_argument("--output", default="run/qa/e2e")
    parser.add_argument("--record-video", action="store_true")
    parser.add_argument("--fail-fast", action="store_true", help="Añade --maxfail=1 durante depuración dirigida")
    parser.add_argument("--tests", default="", help=argparse.SUPPRESS)  # Compatibilidad v0.23.2.8 anterior
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run E2E tests with controlled output, timeout and failure reporting."""

    root = Path(__file__).resolve().parent.parent
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    output = output_from_raw_args(root, raw_argv)
    started = time.monotonic()

    try:
        args = build_parser().parse_args(raw_argv)
        selected = normalize_scenarios(args.scenarios, args.tests)
        browsers = [item.strip().lower() for item in args.browsers.split(",") if item.strip()]
        invalid_browsers = sorted(set(browsers) - {"chromium", "firefox", "webkit"})
        if not browsers or invalid_browsers:
            raise ValueError(
                "Navegadores no permitidos: " + (", ".join(invalid_browsers) if invalid_browsers else "vacío")
            )
    except ValueError as exc:
        return failure_summary(output, message=str(exc), phase="argument-validation", started=started, exit_code=2)

    try:
        if output.exists():
            shutil.rmtree(output)
        output.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return failure_summary(
            output,
            message=f"No se pudo preparar la salida E2E: {exc}",
            phase="output-preparation",
            browsers=browsers,
            selected_scenarios=selected,
            started=started,
        )

    resolved_browsers, missing_browsers = browser_preflight(browsers)
    if missing_browsers:
        message = "Playwright no encontró los navegadores instalados: " + ", ".join(
            f"{name}={path}" for name, path in sorted(missing_browsers.items())
        )
        return failure_summary(
            output,
            message=message,
            phase="browser_preflight",
            browsers=browsers,
            selected_scenarios=selected,
            started=started,
        )

    all_results: list[dict] = []
    commands: list[list[str]] = []
    return_code = 0
    for browser in browsers:
        browser_dir = output / browser
        browser_dir.mkdir(parents=True, exist_ok=True)
        junit = browser_dir / "junit.xml"
        env = os.environ.copy()
        env.update(
            {
                "VINOVA_E2E_ACTIVE": "1",
                "VINOVA_E2E_BROWSER": browser,
                "VINOVA_E2E_ARTIFACT_ROOT": str(output),
                "VINOVA_E2E_RECORD_VIDEO": "True" if args.record_video else "False",
                "DJANGO_ALLOW_ASYNC_UNSAFE": "true",
                "VINOVA_E2E_EXECUTABLE_PATH": resolved_browsers[browser],
            }
        )
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            *(SCENARIOS[name][0] for name in selected),
            "--junitxml",
            str(junit),
        ]
        if args.fail_fast:
            command.append("--maxfail=1")
        commands.append(command)
        try:
            process = subprocess.run(command, cwd=root, env=env, check=False)
            return_code = max(return_code, process.returncode)
        except OSError as exc:
            return_code = max(return_code, 1)
            all_results.append(
                {
                    "browser": browser,
                    "module": "Infraestructura E2E",
                    "test": "pytest-launch",
                    "status": "error",
                    "duration_seconds": 0.0,
                    "message": str(exc),
                }
            )
            continue
        all_results.extend(parse_junit(junit, browser))

    matrix: dict[str, dict] = defaultdict(
        lambda: {"passed": 0, "failed": 0, "error": 0, "skipped": 0, "total": 0}
    )
    for result in all_results:
        row = matrix[result["module"]]
        row[result["status"]] = row.get(result["status"], 0) + 1
        row["total"] += 1

    summary = {
        "schema_version": 1,
        "browsers": browsers,
        "selected_scenarios": selected,
        "fail_fast": args.fail_fast,
        "duration_seconds": round(time.monotonic() - started, 3),
        "status": "passed" if return_code == 0 else "failed",
        "counts": {
            "passed": sum(item["status"] == "passed" for item in all_results),
            "failed": sum(item["status"] in {"failed", "error"} for item in all_results),
            "skipped": sum(item["status"] == "skipped" for item in all_results),
        },
        "module_matrix": dict(sorted(matrix.items())),
        "results": all_results,
        "commands": commands,
    }
    write_summary(output, summary)
    print(
        json.dumps(
            {"status": summary["status"], "counts": summary["counts"], "module_matrix": summary["module_matrix"]},
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"Resumen: {output / 'summary.json'}")
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
