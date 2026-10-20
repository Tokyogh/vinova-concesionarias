#!/usr/bin/env python3
"""ES: Este módulo implementa el componente check javascript para el dominio de operación y QA.

EN: This module implements the check javascript component for the operations and QA domain.

Contexto existente / Existing context:
Operational script for check javascript.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js no está disponible para validar JavaScript.")
    files = sorted((ROOT / "static" / "js").rglob("*.js"))
    if not files:
        raise RuntimeError("No se encontraron archivos JavaScript.")
    failures = []
    for path in files:
        result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True, check=False)
        if result.returncode:
            failures.append(f"{path.relative_to(ROOT)}: {(result.stderr or result.stdout).strip()}")
    if failures:
        raise RuntimeError("\n".join(failures))
    print(f"Sintaxis JavaScript válida en {len(files)} archivos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
