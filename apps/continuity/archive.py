"""ES: Este módulo implementa el componente archive para el dominio de continuidad.

EN: This module implements the archive component for the continuity domain.

Contexto existente / Existing context:
Archive integrity validation for the continuity domain.
"""

from __future__ import annotations

import hashlib
import tarfile
from pathlib import PurePosixPath

from django.conf import settings


class ArchiveValidationError(ValueError):
    pass


def validate_archive_members(archive: tarfile.TarFile, *, allowed_roots: set[str]) -> list[tarfile.TarInfo]:
    members = archive.getmembers()
    if len(members) > settings.VINOVA_ARCHIVE_MAX_MEMBERS:
        raise ArchiveValidationError("El contenedor excede el número máximo de miembros permitido.")
    total_size = sum(member.size for member in members if member.isfile())
    max_total_size = settings.VINOVA_ARCHIVE_MAX_UNCOMPRESSED_MB * 1024 * 1024
    if total_size > max_total_size:
        raise ArchiveValidationError("El contenido descomprimido excede el límite operativo configurado.")
    seen = set()
    for member in members:
        name = member.name
        path = PurePosixPath(name)
        if (
            not name
            or name.startswith(("/", "\\"))
            or "\\" in name
            or ".." in path.parts
            or path.parts[0] not in allowed_roots
            or not (member.isfile() or member.isdir())
        ):
            raise ArchiveValidationError(f"Miembro no permitido en el archivo: {name!r}.")
        if name in seen:
            raise ArchiveValidationError(f"Miembro duplicado en el archivo: {name!r}.")
        seen.add(name)
    return members


def sha256_archive_member(archive: tarfile.TarFile, member: tarfile.TarInfo) -> str:
    source = archive.extractfile(member)
    if source is None:
        raise ArchiveValidationError(f"No se pudo leer {member.name!r}.")
    digest = hashlib.sha256()
    for chunk in iter(lambda: source.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def validate_inventory(archive: tarfile.TarFile, inventory: object) -> None:
    """ES: Valida y normaliza «validate inventory» antes de permitir efectos en continuidad. Además, rechaza estados o entradas inválidas.

    EN: Validates and normalizes «validate inventory» before allowing effects in continuity. It also rejects invalid input or state.
    """

    if not isinstance(inventory, list):
        raise ArchiveValidationError("El inventario interno no es una lista.")
    actual = {member.name: member for member in archive.getmembers() if member.isfile() and member.name != "manifest.json"}
    declared = {}
    for item in inventory:
        if not isinstance(item, dict):
            raise ArchiveValidationError("El inventario contiene una entrada inválida.")
        path = item.get("path")
        if not isinstance(path, str) or path in declared:
            raise ArchiveValidationError("El inventario contiene una ruta inválida o duplicada.")
        declared[path] = item
    if set(actual) != set(declared):
        raise ArchiveValidationError("El inventario no coincide con los archivos del contenedor.")
    for path, member in actual.items():
        item = declared[path]
        if item.get("size_bytes") != member.size:
            raise ArchiveValidationError(f"El tamaño declarado no coincide para {path}.")
        if item.get("sha256") != sha256_archive_member(archive, member):
            raise ArchiveValidationError(f"El SHA-256 interno no coincide para {path}.")
