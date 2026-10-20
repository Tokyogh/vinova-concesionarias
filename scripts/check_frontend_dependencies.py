#!/usr/bin/env python3
"""ES: Este módulo implementa el componente check frontend dependencies para el dominio de operación y QA.

EN: This module implements the check frontend dependencies component for the operations and QA domain.

Contexto existente / Existing context:
Valida dependencias frontend autocontenidas antes de construir staging.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
from pathlib import Path

HTMX_VERSION = "2.0.10"
HTMX_RELATIVE_PATH = Path("static/vendor/htmx/htmx.min.js")
HTMX_SHA384_BASE64 = "H5SrcfygHmAuTDZphMHqBJLc3FhssKjG7w/CeCpFReSfwBWDTKpkzPP8c+cLsK+V"


def sha384_base64(path: Path) -> str:
    digest = hashlib.sha384(path.read_bytes()).digest()
    return base64.b64encode(digest).decode("ascii")


def validate(project_root: Path) -> list[str]:
    errors: list[str] = []
    htmx = project_root / HTMX_RELATIVE_PATH
    if not htmx.is_file():
        errors.append(
            "Falta HTMX local. Ejecute: powershell -ExecutionPolicy Bypass "
            "-File scripts/install_frontend_dependencies.ps1"
        )
        return errors
    actual = sha384_base64(htmx)
    if actual != HTMX_SHA384_BASE64:
        errors.append(
            f"HTMX {HTMX_VERSION} no coincide con el SHA-384 esperado; "
            "vuelva a instalar la dependencia."
        )
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = validate(args.project_root.resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Dependencias frontend validas: HTMX {HTMX_VERSION} local e integro.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
