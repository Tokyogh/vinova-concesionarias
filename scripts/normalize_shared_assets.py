#!/usr/bin/env python3
"""ES: Este módulo implementa el componente normalize shared assets para el dominio de operación y QA.

EN: This module implements the normalize shared assets component for the operations and QA domain.

Contexto existente / Existing context:
Normaliza permisos de staticfiles/media para el Nginx no privilegiado.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_SHARED_GID = 101
DIRECTORY_MODE = 0o2750
FILE_MODE = 0o640
ROOTS = (Path("/app/staticfiles"), Path("/app/media"))


def normalize_tree(root: Path, gid: int) -> tuple[int, int]:
    """Aplica grupo compartido sin seguir enlaces simbólicos."""
    directories = 0
    files = 0
    if not root.exists():
        return directories, files

    candidates = [root, *root.rglob("*")]
    for path in candidates:
        if path.is_symlink():
            continue
        os.chown(path, -1, gid, follow_symlinks=False)
        if path.is_dir():
            path.chmod(DIRECTORY_MODE)
            directories += 1
        elif path.is_file():
            # Static y media no necesitan bit ejecutable. Se elimina acceso de
            # otros usuarios y se concede únicamente lectura al grupo Nginx.
            path.chmod(FILE_MODE)
            files += 1
    return directories, files


def main() -> int:
    raw_gid = os.getenv("VINOVA_SHARED_ASSETS_GID", str(DEFAULT_SHARED_GID)).strip()
    try:
        gid = int(raw_gid)
    except ValueError as exc:
        raise SystemExit("VINOVA_SHARED_ASSETS_GID debe ser un entero positivo.") from exc
    if gid <= 0:
        raise SystemExit("VINOVA_SHARED_ASSETS_GID debe ser un entero positivo.")

    total_directories = 0
    total_files = 0
    for root in ROOTS:
        directories, files = normalize_tree(root, gid)
        total_directories += directories
        total_files += files

    print(
        "Permisos compartidos normalizados: "
        f"gid={gid}, directorios={total_directories}, archivos={total_files}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
