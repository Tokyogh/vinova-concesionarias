"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de continuidad.

EN: This module implements business services and transactional effects for the continuity domain.

Contexto existente / Existing context:
Transactional business services for the continuity domain.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
from collections.abc import Callable
from pathlib import Path, PurePath

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from apps.audit.services import audit_log
from apps.common.lifecycle import ProductVersion, database_migration_state
from apps.continuity.archive import ArchiveValidationError, validate_archive_members, validate_inventory
from apps.continuity.models import BackupPolicy, BackupRecord, RestoreDrill

logger = logging.getLogger(__name__)
BACKUP_FOLDER = "backups"
BACKUP_POLICY_FIELDS = (
    "name",
    "is_active",
    "frequency",
    "retention_days",
    "include_database",
    "include_media",
    "include_private",
    "external_copy_required",
    "destination_hint",
    "next_review_at",
    "notes",
)


@transaction.atomic
def update_backup_policy(*, actor, policy: BackupPolicy, values: dict) -> BackupPolicy:
    current = BackupPolicy.objects.select_for_update().get(pk=policy.pk)
    before = {field: getattr(current, field) for field in BACKUP_POLICY_FIELDS}
    for field in BACKUP_POLICY_FIELDS:
        if field in values:
            setattr(current, field, values[field])
    current.full_clean()
    current.save(update_fields=[*BACKUP_POLICY_FIELDS, "updated_at"])
    audit_log(
        user=actor,
        action="continuity.policy.updated",
        target=current,
        before=before,
        after={field: getattr(current, field) for field in BACKUP_POLICY_FIELDS},
        is_sensitive=True,
    )
    return current


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_add_directory(
    archive: tarfile.TarFile,
    source: Path,
    arcname: str,
    *,
    exclude: set[Path] | None = None,
    skip_relative: Callable[[Path], bool] | None = None,
) -> list[dict]:
    if not source.exists():
        return []
    excluded = {item.resolve() for item in (exclude or set())}
    inventory = []
    for path in source.rglob("*"):
        if path.is_symlink():
            continue
        resolved = path.resolve()
        if any(resolved == item or item in resolved.parents for item in excluded):
            continue
        relative = path.relative_to(source)
        if skip_relative and skip_relative(relative):
            continue
        archive.add(path, arcname=str(Path(arcname) / relative), recursive=False)
        if path.is_file():
            inventory.append(
                {
                    "path": (PurePath(arcname) / relative).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return inventory


def _database_snapshot(destination: Path) -> dict:
    engine = connection.settings_dict.get("ENGINE", "")
    if engine.endswith("sqlite3"):
        source = Path(connection.settings_dict["NAME"])
        target = destination / "database.sqlite3"
        if source.exists():
            shutil.copy2(source, target)
        else:
            target.touch()
        return {"engine": "sqlite3", "filename": target.name, "format": "sqlite"}

    if "postgresql" not in engine:
        raise RuntimeError(f"Motor de base de datos no soportado para backup automático: {engine}")

    cfg = connection.settings_dict
    target = destination / "database.dump"
    command = [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-acl",
        "--file",
        str(target),
        "--host",
        str(cfg.get("HOST") or "db"),
        "--port",
        str(cfg.get("PORT") or "5432"),
        "--username",
        str(cfg.get("USER") or ""),
        str(cfg.get("NAME") or ""),
    ]
    environment = os.environ.copy()
    if cfg.get("PASSWORD"):
        environment["PGPASSWORD"] = str(cfg["PASSWORD"])
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=environment,
            timeout=settings.VINOVA_BACKUP_SOFT_TIME_LIMIT,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("No se encontró pg_dump en el contenedor de aplicación.") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("pg_dump excedió el tiempo máximo configurado.") from exc
    if result.returncode != 0:
        raise RuntimeError((result.stderr or "pg_dump terminó con error.").strip()[:2000])
    return {"engine": "postgresql", "filename": target.name, "format": "custom"}


def create_backup_record(
    *,
    actor,
    backup_type: str,
    notes: str = "",
    execution_mode: str = BackupRecord.ExecutionMode.ASYNC,
) -> BackupRecord:
    policy = BackupPolicy.objects.filter(is_active=True).order_by("created_at").first()
    if not policy:
        policy = BackupPolicy.objects.create()
    record = BackupRecord.objects.create(
        policy=policy,
        backup_type=backup_type,
        initiated_by=actor,
        notes=notes,
        execution_mode=execution_mode,
    )
    audit_log(
        user=actor,
        action="continuity.backup.requested",
        target=record,
        after={"backup_type": backup_type, "execution_mode": execution_mode},
    )
    return record


@transaction.atomic
def mark_backup_failed(record: BackupRecord, message: str) -> BackupRecord:
    record.status = BackupRecord.Status.FAILED
    record.error_message = message[:5000]
    record.completed_at = timezone.now()
    record.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
    audit_log(
        user=record.initiated_by,
        action="continuity.backup.failed",
        target=record,
        after={"error": record.error_message},
        severity="high",
        result="failure",
    )
    return record


def execute_backup(record: BackupRecord) -> BackupRecord:
    """ES: Ejecuta la operación «execute backup» dentro del dominio de continuidad. Además, registra efectos auditables.

    EN: Executes the «execute backup» operation within the continuity domain. It also records auditable effects.
    """

    record.refresh_from_db()
    if record.status in {BackupRecord.Status.COMPLETED, BackupRecord.Status.VERIFIED}:
        return record

    record.status = BackupRecord.Status.RUNNING
    record.started_at = timezone.now()
    record.completed_at = None
    record.error_message = ""
    record.save(update_fields=["status", "started_at", "completed_at", "error_message", "updated_at"])

    backup_root = Path(settings.PRIVATE_STORAGE_ROOT) / BACKUP_FOLDER
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = timezone.localtime().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"vinova_pro_{record.backup_type}_{stamp}_{record.public_id.hex[:8]}.tar.gz"
    destination = backup_root / filename
    partial_destination = backup_root / f".{filename}.partial"

    try:
        with tempfile.TemporaryDirectory(prefix="vinova_backup_") as temp_name:
            temp = Path(temp_name)
            components: dict[str, object] = {}
            if record.backup_type in {BackupRecord.BackupType.FULL, BackupRecord.BackupType.DATABASE}:
                components["database"] = _database_snapshot(temp)
            manifest = {
                "format_version": settings.VINOVA_BACKUP_FORMAT_VERSION,
                "backup_format_version": settings.VINOVA_BACKUP_FORMAT_VERSION,
                "product": "Vinova Pro",
                "product_version": settings.VINOVA_PRODUCT_VERSION,
                "database_migration_state": database_migration_state(),
                "generated_at": timezone.now().isoformat(),
                "backup_id": str(record.public_id),
                "backup_type": record.backup_type,
                "execution_mode": record.execution_mode,
                "components": components,
                "files": {},
                "inventory": [],
                "restore_note": "Restaurar solamente en un entorno aislado y validar antes de reemplazar producción.",
            }
            with tarfile.open(partial_destination, "w:gz") as archive:
                for snapshot in temp.iterdir():
                    archive.add(snapshot, arcname=snapshot.name)
                    manifest["inventory"].append(
                        {
                            "path": snapshot.name,
                            "size_bytes": snapshot.stat().st_size,
                            "sha256": sha256_file(snapshot),
                        }
                    )
                if record.backup_type in {BackupRecord.BackupType.FULL, BackupRecord.BackupType.FILES}:
                    media_inventory = _safe_add_directory(archive, Path(settings.MEDIA_ROOT), "media")
                    private_root = Path(settings.PRIVATE_STORAGE_ROOT)
                    private_inventory = _safe_add_directory(archive, private_root, "private", exclude={backup_root})
                    manifest["inventory"].extend(media_inventory)
                    manifest["inventory"].extend(private_inventory)
                    manifest["files"] = {
                        "media_count": len(media_inventory),
                        "private_count": len(private_inventory),
                    }
                manifest_path = temp / "manifest.json"
                manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
                archive.add(manifest_path, arcname="manifest.json")

        os.replace(partial_destination, destination)
        record.archive_path = str(destination.relative_to(Path(settings.PRIVATE_STORAGE_ROOT)))
        record.filename = filename
        record.size_bytes = destination.stat().st_size
        record.sha256 = sha256_file(destination)
        record.manifest = manifest
        record.status = BackupRecord.Status.COMPLETED
        record.completed_at = timezone.now()
        record.save(
            update_fields=[
                "archive_path",
                "filename",
                "size_bytes",
                "sha256",
                "manifest",
                "status",
                "completed_at",
                "updated_at",
            ]
        )
        if record.policy_id:
            BackupPolicy.objects.filter(pk=record.policy_id).update(last_success_at=record.completed_at)
        audit_log(
            user=record.initiated_by,
            action="continuity.backup.completed",
            target=record,
            after={"sha256": record.sha256, "size_bytes": record.size_bytes},
        )
        logger.info("Backup %s completado (%s bytes)", record.public_id, record.size_bytes)
        return record
    except Exception as exc:  # noqa: BLE001 - se registra la causa operacional
        partial_destination.unlink(missing_ok=True)
        destination.unlink(missing_ok=True)
        logger.exception("Falló el backup %s", record.public_id)
        return mark_backup_failed(record, str(exc))


def backup_archive_path(record: BackupRecord) -> Path:
    path = (Path(settings.PRIVATE_STORAGE_ROOT) / record.archive_path).resolve()
    root = Path(settings.PRIVATE_STORAGE_ROOT).resolve()
    if root not in path.parents:
        raise RuntimeError("Ruta de backup inválida.")
    return path


def backup_restore_compatibility(manifest: dict, *, allow_forward_migration: bool = False) -> dict:
    if manifest.get("product") != "Vinova Pro":
        return {"compatible": False, "reason": "El backup pertenece a otro producto."}
    try:
        source = ProductVersion.parse(str(manifest.get("product_version", "")))
        target = ProductVersion.parse(settings.VINOVA_PRODUCT_VERSION)
    except ValueError as exc:
        return {"compatible": False, "reason": str(exc)}
    if source > target:
        return {"compatible": False, "reason": "El backup proviene de una versión más nueva."}
    if source < target and not allow_forward_migration:
        return {
            "compatible": False,
            "reason": "El backup requiere una ruta de migración forward explícitamente autorizada.",
        }
    return {"compatible": True, "reason": "Compatible"}


def verify_backup(record: BackupRecord, *, actor=None, allow_forward_migration: bool = False) -> dict:
    """ES: Ejecuta la operación «verify backup» dentro del dominio de continuidad. Además, registra efectos auditables, rechaza estados o entradas inválidas.

    EN: Executes the «verify backup» operation within the continuity domain. It also records auditable effects, rejects invalid input or state.
    """

    path = backup_archive_path(record)
    if not path.exists() or not path.is_file():
        return {"valid": False, "reason": "El archivo no existe.", "sha256": ""}
    current_hash = sha256_file(path)
    if record.sha256 and current_hash != record.sha256:
        return {"valid": False, "reason": "El hash SHA-256 no coincide.", "sha256": current_hash}
    try:
        with tarfile.open(path, "r:gz") as archive:
            validate_archive_members(
                archive,
                allowed_roots={"manifest.json", "database.sqlite3", "database.dump", "media", "private"},
            )
            member = archive.getmember("manifest.json")
            if member.size > 1024 * 1024:
                raise ArchiveValidationError("El manifiesto excede 1 MiB.")
            source = archive.extractfile(member)
            manifest = json.loads(source.read().decode("utf-8")) if source else {}
            format_version = manifest.get("backup_format_version", manifest.get("format_version"))
            if format_version not in {2, settings.VINOVA_BACKUP_FORMAT_VERSION}:
                raise ArchiveValidationError("Versión de formato de backup no soportada.")
            if format_version >= 3:
                validate_inventory(archive, manifest.get("inventory"))
    except (
        tarfile.TarError,
        KeyError,
        json.JSONDecodeError,
        UnicodeDecodeError,
        ArchiveValidationError,
    ) as exc:
        return {"valid": False, "reason": f"Archivo o manifiesto inválido: {exc}", "sha256": current_hash}
    valid = str(manifest.get("backup_id")) == str(record.public_id)
    compatibility = backup_restore_compatibility(
        manifest, allow_forward_migration=allow_forward_migration
    )
    if valid:
        record.status = BackupRecord.Status.VERIFIED
        record.verified_at = timezone.now()
        record.verified_by = actor if getattr(actor, "is_authenticated", False) else None
        record.save(update_fields=["status", "verified_at", "verified_by", "updated_at"])
        audit_log(user=actor, action="continuity.backup.verified", target=record, after={"sha256": current_hash})
    return {
        "valid": valid,
        "reason": "OK" if valid else "El manifiesto no pertenece al registro.",
        "sha256": current_hash,
        "manifest": manifest,
        **compatibility,
    }


def create_restore_drill(*, actor, backup: BackupRecord, environment: str, planned_at=None) -> RestoreDrill:
    verification = verify_backup(backup, actor=actor)
    checklist = [
        {"step": "Verificar hash SHA-256", "done": verification["valid"]},
        {"step": "Restaurar en infraestructura aislada", "done": False},
        {"step": "Ejecutar migraciones y django check", "done": False},
        {"step": "Validar login, ventas, inventario, documentos y auditoría", "done": False},
        {"step": "Registrar tiempos y evidencia", "done": False},
        {"step": "Eliminar de forma segura el entorno temporal", "done": False},
    ]
    drill = RestoreDrill.objects.create(
        backup=backup,
        environment=environment,
        planned_at=planned_at,
        performed_by=actor,
        checklist=checklist,
        result_summary="Backup verificado." if verification["valid"] else verification["reason"],
    )
    audit_log(
        user=actor,
        action="continuity.restore_drill.created",
        target=drill,
        after={"backup": str(backup.public_id), "verified": verification["valid"]},
    )
    return drill


def complete_restore_drill(*, actor, drill: RestoreDrill, status: str, result_summary: str) -> RestoreDrill:
    before = {"status": drill.status, "result_summary": drill.result_summary}
    drill.status = status
    drill.result_summary = result_summary
    drill.completed_at = timezone.now()
    evidence = json.dumps(
        {"backup": drill.backup.sha256, "status": status, "summary": result_summary},
        sort_keys=True,
    ).encode()
    drill.evidence_hash = hashlib.sha256(evidence).hexdigest()
    drill.performed_by = actor
    drill.save(
        update_fields=[
            "status",
            "result_summary",
            "completed_at",
            "evidence_hash",
            "performed_by",
            "updated_at",
        ]
    )
    audit_log(
        user=actor,
        action="continuity.restore_drill.completed",
        target=drill,
        before=before,
        after={"status": status, "evidence_hash": drill.evidence_hash},
    )
    return drill
