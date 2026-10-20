#!/usr/bin/env python3
"""ES: Este módulo implementa el componente vinova qa para el dominio de operación y QA.

EN: This module implements the vinova qa component for the operations and QA domain.

Contexto existente / Existing context:
Operational script for vinova qa.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.quality.runner import VALID_PROFILES, run_quality_profile  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Ejecutor aislado del QA Bot de Vinova Pro.")
    parser.add_argument("--profile", choices=sorted(VALID_PROFILES), default="quick")
    parser.add_argument("--report-dir", type=Path, default=ROOT / "private" / "qa_reports")
    parser.add_argument("--allow-sqlite", action="store_true")
    args = parser.parse_args()
    report = run_quality_profile(
        profile=args.profile,
        root=ROOT,
        report_dir=args.report_dir,
        require_postgres=args.profile == "release" and not args.allow_sqlite,
    )
    counts = report["counts"]
    print(
        f"QA {args.profile}: {report['status']} · aprobadas={counts['passed']} · "
        f"advertencias={counts['warning']} · fallidas={counts['failed']}"
    )
    print(f"JSON: {args.report_dir.resolve() / report['report_json_path']}")
    print(f"HTML: {args.report_dir.resolve() / report['report_html_path']}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
