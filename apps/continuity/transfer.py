"""ES: Este módulo implementa el componente transfer para el dominio de continuidad.

EN: This module implements the transfer component for the continuity domain.

Contexto existente / Existing context:
Transfer support for the continuity domain.
"""

from __future__ import annotations

import json
import os
import shutil
import tarfile
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.utils import timezone

from apps.common.lifecycle import ProductVersion, database_migration_state
from apps.continuity.archive import (
    ArchiveValidationError,
    validate_archive_members,
    validate_inventory,
)
from apps.continuity.services import _safe_add_directory, sha256_file


TRANSFER_KIND = "vinova-installation-transfer"
SECRET_FILENAMES = {".env", ".env.staging", ".env.production", "qa_credentials.txt"}
SECRET_SUFFIXES = {".key", ".pem", ".p12", ".pfx", ".crt"}
NON_PORTABLE_DIRECTORIES = {"backups", "qa_reports", "certs", "sessions"}
FIXTURE_EXCLUDES = [
    "admin.logentry",
    "contenttypes.contenttype",
    "auth.permission",
    "sessions.session",
    "security_center.passwordhistory",
    "security_center.activesession",
]
SECRET_FIELD_REDACTIONS = {
    "accounts.user": {"password": "!"},
    "api.apiclient": {"secret_digest": "", "secret_last_four": "", "is_active": False},
    "api.webhookendpoint": {"encrypted_secret": "", "secret_last_four": "", "is_active": False},
    "security_center.usersecurityprofile": {
        "two_factor_enabled": False,
        "encrypted_totp_secret": "",
        "backup_code_hashes": [],
        "two_factor_confirmed_at": None,
        "last_two_factor_at": None,
        "backup_codes_generated_at": None,
    },
}


class TransferValidationError(ValueError):
    pass


def _is_non_portable_private(relative: Path) -> bool:
    lowered_parts = {part.lower() for part in relative.parts}
    name = relative.name.lower()
    return bool(
        lowered_parts.intersection(NON_PORTABLE_DIRECTORIES)
        or name.startswith(".env")
        or name in SECRET_FILENAMES
        or relative.suffix.lower() in SECRET_SUFFIXES
    )


def _portable_database_export(destination: Path) -> dict:
    raw = destination.with_suffix(".raw.json")
    with raw.open("w", encoding="utf-8", newline="") as output:
        call_command(
            "dumpdata",
            use_base_manager=True,
            exclude=FIXTURE_EXCLUDES,
            stdout=output,
        )
    payload = json.loads(raw.read_text(encoding="utf-8"))
    redaction_counts = {model: 0 for model in SECRET_FIELD_REDACTIONS}
    for item in payload:
        model = item.get("model")
        replacements = SECRET_FIELD_REDACTIONS.get(model)
        if replacements:
            item["fields"].update(replacements)
            redaction_counts[model] += 1
    destination.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    raw.unlink(missing_ok=True)
    return {
        "engine": "portable",
        "filename": destination.name,
        "format": "django-json-fixture",
        "object_count": len(payload),
        "excluded_models": FIXTURE_EXCLUDES,
        "secret_redactions": redaction_counts,
    }


def export_installation_transfer(destination: Path) -> dict:
    """ES: Ejecuta la operación «export installation transfer» dentro del dominio de continuidad. Además, rechaza estados o entradas inválidas.

    EN: Executes the «export installation transfer» operation within the continuity domain. It also rejects invalid input or state.
    """

    destination = destination.resolve()
    if destination.suffix.lower() != ".vinova":
        raise TransferValidationError("El archivo de transfer debe usar la extensión .vinova.")
    if destination.exists():
        raise TransferValidationError("El archivo de destino ya existe; no se sobrescribirá.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(f".{destination.name}.partial")

    try:
        with tempfile.TemporaryDirectory(prefix="vinova_transfer_") as temp_name:
            temp = Path(temp_name)
            database_path = temp / "database.json"
            database = _portable_database_export(database_path)
            manifest = {
                "kind": TRANSFER_KIND,
                "transfer_format_version": settings.VINOVA_TRANSFER_FORMAT_VERSION,
                "product_version": settings.VINOVA_PRODUCT_VERSION,
                "database_migration_state": database_migration_state(),
                "generated_at": timezone.now().isoformat(),
                "components": {"database": database, "media": {}, "private": {}},
                "inventory": [],
                "secrets": {
                    "included": False,
                    "reprovision": [
                        "SECRET_KEY",
                        "database credentials",
                        "Redis credentials",
                        "email credentials",
                        "object-storage credentials",
                        "TLS certificates",
                    ],
                },
            }
            with tarfile.open(partial, "w:gz") as archive:
                database_arcname = f"payload/{database_path.name}"
                archive.add(database_path, arcname=database_arcname)
                manifest["inventory"].append(
                    {
                        "path": database_arcname,
                        "size_bytes": database_path.stat().st_size,
                        "sha256": sha256_file(database_path),
                    }
                )
                media_inventory = _safe_add_directory(
                    archive, Path(settings.MEDIA_ROOT), "payload/media"
                )
                private_inventory = _safe_add_directory(
                    archive,
                    Path(settings.PRIVATE_STORAGE_ROOT),
                    "payload/private",
                    exclude={partial, destination},
                    skip_relative=_is_non_portable_private,
                )
                manifest["inventory"].extend(media_inventory)
                manifest["inventory"].extend(private_inventory)
                manifest["components"]["media"] = {"file_count": len(media_inventory)}
                manifest["components"]["private"] = {"file_count": len(private_inventory)}
                manifest_path = temp / "manifest.json"
                manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
                archive.add(manifest_path, arcname="manifest.json")
        os.replace(partial, destination)
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    return {
        "path": str(destination),
        "size_bytes": destination.stat().st_size,
        "sha256": sha256_file(destination),
        "manifest": manifest,
    }


def validate_installation_transfer(
    package: Path,
    *,
    target_product_version: str | None = None,
    allow_forward_migration: bool = False,
    destination_root: Path | None = None,
) -> dict:
    """Validate a signed installation package without applying its contents."""

    package = package.resolve()
    if package.suffix.lower() != ".vinova" or not package.is_file():
        raise TransferValidationError("El paquete .vinova no existe o tiene una extensión inválida.")
    target = ProductVersion.parse(target_product_version or settings.VINOVA_PRODUCT_VERSION)
    try:
        with tarfile.open(package, "r:gz") as archive:
            validate_archive_members(archive, allowed_roots={"manifest.json", "payload"})
            manifest_member = archive.getmember("manifest.json")
            if manifest_member.size > 1024 * 1024:
                raise TransferValidationError("El manifiesto excede 1 MiB.")
            source = archive.extractfile(manifest_member)
            manifest = json.loads(source.read().decode("utf-8")) if source else {}
            if manifest.get("kind") != TRANSFER_KIND:
                raise TransferValidationError("El archivo no es un transfer de instalación VINOVA.")
            if manifest.get("transfer_format_version") != settings.VINOVA_TRANSFER_FORMAT_VERSION:
                raise TransferValidationError("La versión del formato de transfer no es compatible.")
            source_version = ProductVersion.parse(str(manifest.get("product_version", "")))
            if source_version > target:
                raise TransferValidationError("El paquete proviene de una versión más nueva que el destino.")
            if source_version < target and not allow_forward_migration:
                raise TransferValidationError("El paquete requiere una ruta de migración forward explícitamente autorizada.")
            if manifest.get("secrets", {}).get("included") is not False:
                raise TransferValidationError("El manifest no confirma la exclusión de secretos.")
            validate_inventory(archive, manifest.get("inventory"))
            required_bytes = sum(item["size_bytes"] for item in manifest["inventory"])
    except (tarfile.TarError, KeyError, json.JSONDecodeError, UnicodeDecodeError, ArchiveValidationError, ValueError) as exc:
        if isinstance(exc, TransferValidationError):
            raise
        raise TransferValidationError(f"Paquete de transfer inválido: {exc}") from exc

    if destination_root is not None:
        destination_root = destination_root.resolve()
        probe = destination_root if destination_root.exists() else destination_root.parent
        if not probe.exists() or shutil.disk_usage(probe).free < required_bytes * 2:
            raise TransferValidationError("Espacio libre insuficiente para preparar y validar la importación.")
    return {
        "valid": True,
        "sha256": sha256_file(package),
        "size_bytes": package.stat().st_size,
        "required_bytes": required_bytes,
        "manifest": manifest,
    }


def prepare_installation_import(
    package: Path,
    destination: Path,
    *,
    allow_forward_migration: bool = False,
) -> dict:
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise TransferValidationError("El directorio de preparación debe estar vacío.")
    validation = validate_installation_transfer(
        package,
        allow_forward_migration=allow_forward_migration,
        destination_root=destination,
    )
    with tarfile.open(package, "r:gz") as archive:
        validate_archive_members(archive, allowed_roots={"manifest.json", "payload"})
        archive.extractall(destination, filter="data")
    return validation
