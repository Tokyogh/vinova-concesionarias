"""ES: Este módulo implementa el componente update manifest para el dominio de infraestructura compartida.

EN: This module implements the update manifest component for the common domain.

Contexto existente / Existing context:
Update manifest support for the common domain.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import shutil
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from django.conf import settings
from django.db import connection

from apps.common.lifecycle import assess_product_upgrade, database_migration_state


RELEASE_MANIFEST_SCHEMA_VERSION = 1
RELEASE_CHANNELS = {"stable", "internal"}


class ReleaseManifestError(ValueError):
    pass


def canonical_release_payload(manifest: dict) -> bytes:
    unsigned = {key: value for key, value in manifest.items() if key != "signature"}
    return json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def validate_release_manifest(manifest: object) -> dict:
    """ES: Valida y normaliza «validate release manifest» antes de permitir efectos en infraestructura compartida.

    EN: Validates and normalizes «validate release manifest» before allowing effects in common.
    """

    if not isinstance(manifest, dict):
        raise ReleaseManifestError("El release manifest debe ser un objeto JSON.")
    required = {"schema_version", "product", "version", "channel", "published_at", "artifact", "compatibility", "signature"}
    missing = required.difference(manifest)
    if missing:
        raise ReleaseManifestError(f"Faltan campos obligatorios: {', '.join(sorted(missing))}.")
    if manifest["schema_version"] != RELEASE_MANIFEST_SCHEMA_VERSION or manifest["product"] != "Vinova Pro":
        raise ReleaseManifestError("Schema o producto del release no soportado.")
    if manifest["channel"] not in RELEASE_CHANNELS:
        raise ReleaseManifestError("Canal de release no soportado.")
    artifact = manifest["artifact"]
    if not isinstance(artifact, dict) or set(("filename", "size_bytes", "sha256")) - set(artifact):
        raise ReleaseManifestError("Metadata de artefacto incompleta.")
    if not isinstance(artifact["size_bytes"], int) or artifact["size_bytes"] <= 0:
        raise ReleaseManifestError("Tamaño de artefacto inválido.")
    if not isinstance(artifact["sha256"], str) or len(artifact["sha256"]) != 64:
        raise ReleaseManifestError("SHA-256 de artefacto inválido.")
    compatibility = manifest["compatibility"]
    if not isinstance(compatibility, dict) or not isinstance(compatibility.get("supported_from"), list):
        raise ReleaseManifestError("Contrato de compatibilidad inválido.")
    signature = manifest["signature"]
    if not isinstance(signature, dict) or signature.get("algorithm") != "ed25519":
        raise ReleaseManifestError("Firma Ed25519 obligatoria.")
    if not signature.get("key_id") or not signature.get("value"):
        raise ReleaseManifestError("Firma incompleta.")
    return manifest


def load_release_manifest(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ReleaseManifestError(f"No se pudo leer el release manifest: {exc}") from exc
    return validate_release_manifest(payload)


def verify_release_signature(manifest: dict, public_key: bytes, *, expected_key_id: str) -> bool:
    validate_release_manifest(manifest)
    if manifest["signature"]["key_id"] != expected_key_id:
        raise ReleaseManifestError("La firma no usa la clave de release configurada.")
    try:
        loaded = serialization.load_pem_public_key(public_key)
        if not isinstance(loaded, Ed25519PublicKey):
            raise ReleaseManifestError("La clave pública no es Ed25519.")
        signature = base64.b64decode(manifest["signature"]["value"], validate=True)
        loaded.verify(signature, canonical_release_payload(manifest))
    except (ValueError, TypeError, binascii.Error) as exc:
        raise ReleaseManifestError(f"Firma de release inválida: {exc}") from exc
    except Exception as exc:  # cryptography InvalidSignature, sin filtrar detalles sensibles
        raise ReleaseManifestError("Firma de release inválida.") from exc
    return True


def verify_release_artifact(manifest: dict, artifact_path: Path) -> bool:
    artifact = manifest["artifact"]
    if not artifact_path.is_file() or artifact_path.name != artifact["filename"]:
        raise ReleaseManifestError("El artefacto no existe o su nombre no coincide.")
    if artifact_path.stat().st_size != artifact["size_bytes"]:
        raise ReleaseManifestError("El tamaño del artefacto no coincide.")
    digest_builder = hashlib.sha256()
    with artifact_path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest_builder.update(chunk)
    digest = digest_builder.hexdigest()
    if digest != artifact["sha256"]:
        raise ReleaseManifestError("El SHA-256 del artefacto no coincide.")
    return True


def run_update_preflight(
    manifest: dict,
    *,
    public_key: bytes,
    trusted_key_id: str,
    artifact_path: Path,
    backup=None,
    require_postgresql: bool = True,
    dependency_health: dict[str, bool] | None = None,
) -> dict:
    """Preflight read-only. No descarga, migra, reinicia ni despliega servicios."""
    checks = []

    def check(name: str, passed: bool, detail: str):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    try:
        verify_release_signature(manifest, public_key, expected_key_id=trusted_key_id)
        check("release.signature", True, "Firma Ed25519 válida.")
    except ReleaseManifestError as exc:
        check("release.signature", False, str(exc))
    try:
        verify_release_artifact(manifest, artifact_path)
        check("release.artifact", True, "Tamaño y SHA-256 válidos.")
    except ReleaseManifestError as exc:
        check("release.artifact", False, str(exc))

    current = settings.VINOVA_PRODUCT_VERSION
    compatibility = manifest.get("compatibility", {})
    assessment = assess_product_upgrade(
        current,
        str(manifest.get("version", "")),
        migration_path_available=current in compatibility.get("supported_from", []),
        release_compatible=current in compatibility.get("supported_from", []),
    )
    check("release.compatibility", assessment["allowed"], assessment["reason"])

    migration = database_migration_state()
    check("database.migrations", migration["is_current"], f"{migration['pending_count']} migraciones pendientes.")
    backup_ready = bool(
        backup
        and getattr(backup, "status", None) == "verified"
        and getattr(backup, "verified_at", None)
        and getattr(backup, "sha256", "")
        and getattr(backup, "manifest", {}).get("product_version") == current
    )
    check("backup.verified", backup_ready, "Se requiere un backup verificado de la versión instalada.")

    database_ok = connection.vendor == "postgresql" or not require_postgresql
    check("database.engine", database_ok, f"Motor detectado: {connection.vendor}.")
    free_bytes = shutil.disk_usage(artifact_path.parent).free
    needed = manifest.get("artifact", {}).get("size_bytes", 0) * 3
    check("storage.free", free_bytes >= needed, f"Libre={free_bytes}; mínimo={needed}.")
    for dependency, healthy in sorted((dependency_health or {}).items()):
        check(f"dependency.{dependency}", healthy, "Disponible." if healthy else "No disponible.")

    return {
        "ready": all(item["passed"] for item in checks),
        "current_version": current,
        "target_version": manifest.get("version"),
        "checks": checks,
        "boundary": "read-only-preflight-no-deploy-privileges",
    }
