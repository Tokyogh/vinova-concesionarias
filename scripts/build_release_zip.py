#!/usr/bin/env python3
"""ES: Este módulo implementa el componente build release zip para el dominio de operación y QA.

EN: This module implements the build release zip component for the operations and QA domain.

Contexto existente / Existing context:
Construye y verifica el ZIP limpio de una entrega de Vinova Pro.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath

DEFAULT_ROOT_NAME = "VINOVA-PRO-v2.0.0-FINAL-STAGING-READY"
EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    ".venv-smoke",
    "__pycache__",
    "backups",
    "htmlcov",
    "logs",
    "node_modules",
    "playwright-report",
    "qa-reports",
    "qa_reports",
    "security-reports",
    "test-results",
    "trivy-reports",
    ".trivy-cache",
    "staticfiles",
    "venv",
}
EXCLUDED_FILE_NAMES = {
    ".coverage",
    ".env",
    "celerybeat-schedule",
    "nd.txt",
    "test.sqlite3",
}
EXCLUDED_SUFFIXES = {
    ".crt",
    ".db",
    ".dump",
    ".key",
    ".log",
    ".p12",
    ".pem",
    ".pfx",
    ".pyc",
    ".sqlite",
    ".sqlite3",
}
PRIVATE_TOP_LEVEL = {"media", "private", "run"}
ALLOWED_PLACEHOLDERS = {".gitkeep"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()




def archive_mode(relative: Path, source_mode: int) -> int:
    """Normaliza permisos POSIX para que el ZIP sea portable desde Windows."""
    if relative.suffix.lower() == ".sh":
        return 0o755
    return source_mode & 0o777


def should_include(relative: Path) -> bool:
    """ES: Ejecuta la operación «should include» dentro del dominio de operación y QA.

    EN: Executes the «should include» operation within the operations and QA domain.
    """

    parts = relative.parts
    if any(part in EXCLUDED_DIRECTORY_NAMES for part in parts[:-1]):
        return False
    if relative.name in EXCLUDED_FILE_NAMES:
        return False
    allowed_environment_examples = {
        ".env.example",
        ".env.production.example",
        ".env.staging.example",
    }
    if (
        relative.name.startswith(".env")
        and relative.name not in allowed_environment_examples
    ):
        return False
    if relative.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if parts and parts[0] in PRIVATE_TOP_LEVEL and relative.name not in ALLOWED_PLACEHOLDERS:
        return False
    if parts and parts[0] == "docker" and "certs" in parts and relative.name not in ALLOWED_PLACEHOLDERS:
        return False
    return True


def iter_source_files(source: Path, output: Path) -> list[Path]:
    files: list[Path] = []
    output_resolved = output.resolve()
    checksum_resolved = output.with_suffix(output.suffix + ".sha256").resolve()
    for current, directory_names, file_names in os.walk(source, followlinks=False):
        current_path = Path(current)
        directory_names[:] = sorted(
            name
            for name in directory_names
            if name not in EXCLUDED_DIRECTORY_NAMES and not (current_path / name).is_symlink()
        )
        for file_name in sorted(file_names):
            path = current_path / file_name
            if path.is_symlink():
                continue
            resolved = path.resolve()
            if resolved in {output_resolved, checksum_resolved}:
                continue
            relative = path.relative_to(source)
            if should_include(relative):
                files.append(path)
    return files


def write_zip(source: Path, output: Path, root_name: str) -> int:
    files = iter_source_files(source, output)
    if not files:
        raise RuntimeError("No se encontraron archivos para empaquetar.")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in files:
                relative = path.relative_to(source).as_posix()
                arcname = f"{root_name}/{relative}"
                info = zipfile.ZipInfo.from_file(path, arcname=arcname)
                info.compress_type = zipfile.ZIP_DEFLATED
                info._compresslevel = 9
                mode = archive_mode(Path(relative), path.stat().st_mode)
                info.external_attr = (stat.S_IFREG | mode) << 16
                with path.open("rb") as source_handle, archive.open(info, "w", force_zip64=True) as target_handle:
                    while chunk := source_handle.read(1024 * 1024):
                        target_handle.write(chunk)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return len(files)


def verify_zip(path: Path, root_name: str) -> int:
    """ES: Ejecuta la operación «verify zip» dentro del dominio de operación y QA.

    EN: Executes the «verify zip» operation within the operations and QA domain.
    """

    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if not names:
            raise RuntimeError("El ZIP quedó vacío.")
        for name in names:
            pure = PurePosixPath(name)
            if pure.is_absolute() or ".." in pure.parts:
                raise RuntimeError(f"Entrada insegura en ZIP: {name}")
            if not pure.parts or pure.parts[0] != root_name:
                raise RuntimeError(f"Entrada fuera de la carpeta raíz esperada: {name}")
            relative = Path(*pure.parts[1:])
            if not should_include(relative):
                raise RuntimeError(f"Artefacto excluido encontrado en ZIP: {name}")
            info = archive.getinfo(name)
            if info.is_dir():
                continue
            archived_mode = (info.external_attr >> 16) & 0o777
            if relative.suffix.lower() == ".sh" and not (archived_mode & 0o111):
                raise RuntimeError(f"Script shell no ejecutable dentro del ZIP: {name}")
            with archive.open(name) as handle:
                while handle.read(1024 * 1024):
                    pass
        return len(names)


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=project_root, help="Raíz del proyecto que se empaquetará.")
    parser.add_argument(
        "--output",
        type=Path,
        default=project_root.parent / f"{DEFAULT_ROOT_NAME}.zip",
        help="Ruta de salida del ZIP.",
    )
    parser.add_argument("--root-name", default=DEFAULT_ROOT_NAME, help="Carpeta raíz dentro del ZIP.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    if not source.is_dir():
        print(f"No existe la raíz del proyecto: {source}", file=sys.stderr)
        return 2
    if not args.root_name or "/" in args.root_name or "\\" in args.root_name:
        print("--root-name debe ser un nombre de carpeta simple.", file=sys.stderr)
        return 2
    try:
        file_count = write_zip(source, output, args.root_name)
        entry_count = verify_zip(output, args.root_name)
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"No se pudo construir el release: {exc}", file=sys.stderr)
        return 1
    digest = sha256_file(output)
    checksum = output.with_suffix(output.suffix + ".sha256")
    checksum.write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    print(f"ZIP limpio: {output}")
    print(f"Archivos fuente incluidos: {file_count}")
    print(f"Entradas verificadas: {entry_count}")
    print(f"SHA-256: {digest}")
    print(f"Checksum: {checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
