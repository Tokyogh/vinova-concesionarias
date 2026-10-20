#!/usr/bin/env python3
"""ES: Este módulo implementa el componente check release package para el dominio de operación y QA.

EN: This module implements the check release package component for the operations and QA domain.

Contexto existente / Existing context:
Operational script for check release package.
"""

from __future__ import annotations

import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_release_zip import sha256_file, verify_zip, write_zip  # noqa: E402
ROOT_NAME = "VINOVA-PRO-v2.0.0-FINAL-STAGING-READY"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="vinova-release-check-") as temp_name:
        output = Path(temp_name) / f"{ROOT_NAME}.zip"
        files = write_zip(ROOT, output, ROOT_NAME)
        entries = verify_zip(output, ROOT_NAME)
        digest = sha256_file(output)
        if len(digest) != 64:
            raise RuntimeError("Checksum SHA-256 inválido.")
        print(f"ZIP temporal limpio: {files} archivos, {entries} entradas, SHA-256 {digest}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
