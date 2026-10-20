"""ES: Este módulo especifica regresiones ejecutables para el dominio de continuidad.

EN: This module specifies executable regressions for the continuity domain.

Contexto existente / Existing context:
Regression coverage for transfer in the continuity domain.
"""

import io
import json
import tarfile
from collections import namedtuple
from pathlib import Path

import pytest
from django.test import override_settings

from apps.api.models import APIClient
from apps.continuity.transfer import (
    TransferValidationError,
    export_installation_transfer,
    prepare_installation_import,
    validate_installation_transfer,
)


pytestmark = pytest.mark.django_db


def _roots(tmp_path):
    media = tmp_path / "media"
    private = tmp_path / "private"
    media.mkdir()
    private.mkdir()
    (media / "vehicle.webp").write_bytes(b"vehicle-image")
    (private / "documents").mkdir()
    (private / "documents" / "contract.pdf").write_bytes(b"portable-document")
    (private / ".env").write_text("SECRET_KEY=not-portable", encoding="utf-8")
    (private / "qa_credentials.txt").write_text("not-portable", encoding="utf-8")
    (private / "certs").mkdir()
    (private / "certs" / "server.key").write_text("not-portable", encoding="utf-8")
    return media, private


def _rewrite_manifest(source: Path, destination: Path, mutate):
    with tarfile.open(source, "r:gz") as original, tarfile.open(destination, "w:gz") as target:
        for member in original.getmembers():
            content = original.extractfile(member).read() if member.isfile() else None
            if member.name == "manifest.json":
                payload = json.loads(content.decode("utf-8"))
                mutate(payload)
                content = json.dumps(payload).encode("utf-8")
                member.size = len(content)
            target.addfile(member, io.BytesIO(content) if content is not None else None)


def test_transfer_happy_path_excludes_secrets_and_prepares_only(tmp_path, django_user_model):
    media, private = _roots(tmp_path)
    package = tmp_path / "installation.vinova"
    prepared = tmp_path / "prepared"
    user = django_user_model.objects.create_user(
        username="portable-user", email="portable@example.com", password="MustNotTravel-2026!"
    )
    client = APIClient.objects.create(name="Portable API", service_user=user, is_active=True)
    client.set_secret("must-not-travel")
    client.save(update_fields=["secret_digest", "secret_last_four"])

    with override_settings(MEDIA_ROOT=media, PRIVATE_STORAGE_ROOT=private):
        exported = export_installation_transfer(package)
        validated = validate_installation_transfer(package, destination_root=prepared)
        prepared_result = prepare_installation_import(package, prepared)

    assert exported["sha256"] == validated["sha256"] == prepared_result["sha256"]
    assert validated["manifest"]["secrets"]["included"] is False
    assert (prepared / "payload" / "media" / "vehicle.webp").read_bytes() == b"vehicle-image"
    assert (prepared / "payload" / "private" / "documents" / "contract.pdf").exists()
    assert not (prepared / "payload" / "private" / ".env").exists()
    assert not (prepared / "payload" / "private" / "qa_credentials.txt").exists()
    assert not (prepared / "payload" / "private" / "certs").exists()
    assert not any(path.name == "manage.py" for path in prepared.rglob("*"))
    fixture = json.loads((prepared / "payload" / "database.json").read_text(encoding="utf-8"))
    exported_user = next(item for item in fixture if item["model"] == "accounts.user" and item["pk"] == user.pk)
    exported_client = next(item for item in fixture if item["model"] == "api.apiclient" and item["pk"] == client.pk)
    assert exported_user["fields"]["password"] == "!"
    assert exported_client["fields"]["secret_digest"] == ""
    assert exported_client["fields"]["secret_last_four"] == ""
    assert exported_client["fields"]["is_active"] is False


def test_transfer_rejects_newer_product_version(tmp_path):
    media, private = _roots(tmp_path)
    package = tmp_path / "installation.vinova"
    newer = tmp_path / "newer.vinova"
    with override_settings(MEDIA_ROOT=media, PRIVATE_STORAGE_ROOT=private):
        export_installation_transfer(package)
        _rewrite_manifest(package, newer, lambda manifest: manifest.update(product_version="99.0.0"))
        with pytest.raises(TransferValidationError, match="versión más nueva"):
            validate_installation_transfer(newer)


def test_transfer_requires_explicit_forward_migration_for_older_package(tmp_path):
    media, private = _roots(tmp_path)
    package = tmp_path / "installation.vinova"
    older = tmp_path / "older.vinova"
    with override_settings(MEDIA_ROOT=media, PRIVATE_STORAGE_ROOT=private):
        export_installation_transfer(package)
        _rewrite_manifest(package, older, lambda manifest: manifest.update(product_version="1.0.0"))
        with pytest.raises(TransferValidationError, match="ruta de migración forward"):
            validate_installation_transfer(older)
        assert validate_installation_transfer(older, allow_forward_migration=True)["valid"]


def test_transfer_rejects_inventory_mismatch(tmp_path):
    media, private = _roots(tmp_path)
    package = tmp_path / "installation.vinova"
    damaged = tmp_path / "damaged.vinova"
    with override_settings(MEDIA_ROOT=media, PRIVATE_STORAGE_ROOT=private):
        export_installation_transfer(package)
        _rewrite_manifest(
            package,
            damaged,
            lambda manifest: manifest["inventory"][0].update(sha256="0" * 64),
        )
        with pytest.raises(TransferValidationError, match="SHA-256 interno"):
            validate_installation_transfer(damaged)


def test_transfer_rejects_path_traversal_member(tmp_path):
    package = tmp_path / "traversal.vinova"
    with tarfile.open(package, "w:gz") as archive:
        member = tarfile.TarInfo("../escape.txt")
        member.size = 6
        archive.addfile(member, io.BytesIO(b"escape"))

    with pytest.raises(TransferValidationError, match="Miembro no permitido"):
        validate_installation_transfer(package)


def test_transfer_rejects_too_many_archive_members(tmp_path, settings):
    media, private = _roots(tmp_path)
    package = tmp_path / "installation.vinova"
    with override_settings(MEDIA_ROOT=media, PRIVATE_STORAGE_ROOT=private):
        export_installation_transfer(package)
    settings.VINOVA_ARCHIVE_MAX_MEMBERS = 1

    with pytest.raises(TransferValidationError, match="máximo de miembros"):
        validate_installation_transfer(package)


def test_transfer_rejects_excessive_uncompressed_archive_size(tmp_path, settings):
    media, private = _roots(tmp_path)
    package = tmp_path / "installation.vinova"
    with override_settings(MEDIA_ROOT=media, PRIVATE_STORAGE_ROOT=private):
        export_installation_transfer(package)
    settings.VINOVA_ARCHIVE_MAX_UNCOMPRESSED_MB = 0

    with pytest.raises(TransferValidationError, match="descomprimido excede"):
        validate_installation_transfer(package)


def test_prepare_import_requires_empty_destination(tmp_path):
    media, private = _roots(tmp_path)
    package = tmp_path / "installation.vinova"
    destination = tmp_path / "occupied"
    destination.mkdir()
    (destination / "keep.txt").write_text("preserve", encoding="utf-8")
    with override_settings(MEDIA_ROOT=media, PRIVATE_STORAGE_ROOT=private):
        export_installation_transfer(package)
        with pytest.raises(TransferValidationError, match="debe estar vacío"):
            prepare_installation_import(package, destination)

    assert (destination / "keep.txt").read_text(encoding="utf-8") == "preserve"


def test_transfer_preflight_rejects_insufficient_space(tmp_path, monkeypatch):
    media, private = _roots(tmp_path)
    package = tmp_path / "installation.vinova"
    destination = tmp_path / "staging"
    destination.mkdir()
    usage = namedtuple("usage", "total used free")
    with override_settings(MEDIA_ROOT=media, PRIVATE_STORAGE_ROOT=private):
        export_installation_transfer(package)
        monkeypatch.setattr("apps.continuity.transfer.shutil.disk_usage", lambda _path: usage(100, 100, 0))
        with pytest.raises(TransferValidationError, match="Espacio libre insuficiente"):
            validate_installation_transfer(package, destination_root=destination)
