"""ES: Este módulo especifica regresiones ejecutables para el dominio de infraestructura compartida.

EN: This module specifies executable regressions for the common domain.

Contexto existente / Existing context:
Regression coverage for update manifest in the common domain.
"""

import base64
import hashlib
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.conf import settings
from django.utils import timezone

from apps.common.update_manifest import (
    ReleaseManifestError,
    canonical_release_payload,
    run_update_preflight,
    verify_release_artifact,
    verify_release_signature,
)


def _signed_release(tmp_path, *, supported_from=None, version="2.1.0"):
    artifact = tmp_path / "vinova-pro-2.1.0.tar.gz"
    artifact.write_bytes(b"signed-release-artifact")
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    manifest = {
        "schema_version": 1,
        "product": "Vinova Pro",
        "version": version,
        "channel": "stable",
        "published_at": "2026-10-07T00:00:00Z",
        "artifact": {
            "filename": artifact.name,
            "size_bytes": artifact.stat().st_size,
            "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        },
        "compatibility": {"supported_from": supported_from or [settings.VINOVA_PRODUCT_VERSION]},
        "signature": {"algorithm": "ed25519", "key_id": "release-2026", "value": "pending"},
    }
    signature = private_key.sign(canonical_release_payload(manifest))
    manifest["signature"]["value"] = base64.b64encode(signature).decode("ascii")
    return manifest, artifact, public_key


def _verified_backup():
    return SimpleNamespace(
        status="verified",
        verified_at=timezone.now(),
        sha256="a" * 64,
        manifest={"product_version": settings.VINOVA_PRODUCT_VERSION},
    )


def test_release_signature_and_artifact_are_verified(tmp_path):
    manifest, artifact, public_key = _signed_release(tmp_path)

    assert verify_release_signature(manifest, public_key, expected_key_id="release-2026")
    assert verify_release_artifact(manifest, artifact)


def test_release_signature_rejects_tampered_manifest(tmp_path):
    manifest, _, public_key = _signed_release(tmp_path)
    manifest["version"] = "9.9.9"

    with pytest.raises(ReleaseManifestError, match="Firma de release inválida"):
        verify_release_signature(manifest, public_key, expected_key_id="release-2026")


def test_release_signature_rejects_untrusted_key_id(tmp_path):
    manifest, _, public_key = _signed_release(tmp_path)

    with pytest.raises(ReleaseManifestError, match="clave de release configurada"):
        verify_release_signature(manifest, public_key, expected_key_id="different-key")


def test_release_artifact_rejects_tampering(tmp_path):
    manifest, artifact, _ = _signed_release(tmp_path)
    artifact.write_bytes(b"tampered")

    with pytest.raises(ReleaseManifestError, match="tamaño|SHA-256"):
        verify_release_artifact(manifest, artifact)


@pytest.mark.django_db
def test_update_preflight_happy_path_is_read_only(tmp_path):
    manifest, artifact, public_key = _signed_release(tmp_path)

    result = run_update_preflight(
        manifest,
        public_key=public_key,
        trusted_key_id="release-2026",
        artifact_path=artifact,
        backup=_verified_backup(),
        require_postgresql=False,
        dependency_health={"redis": True, "workers": True},
    )

    assert result["ready"]
    assert result["boundary"] == "read-only-preflight-no-deploy-privileges"
    assert all(check["passed"] for check in result["checks"])


@pytest.mark.django_db
def test_update_preflight_fails_closed_without_compatibility_or_backup(tmp_path):
    manifest, artifact, public_key = _signed_release(tmp_path, supported_from=["1.0.0"])

    result = run_update_preflight(
        manifest,
        public_key=public_key,
        trusted_key_id="release-2026",
        artifact_path=artifact,
        backup=None,
        require_postgresql=False,
    )
    checks = {item["name"]: item["passed"] for item in result["checks"]}

    assert not result["ready"]
    assert not checks["release.compatibility"]
    assert not checks["backup.verified"]


def test_production_compose_keeps_web_outside_privileged_updater_boundary():
    compose = (settings.BASE_DIR / "docker-compose.prod.yml").read_text(encoding="utf-8")

    assert "docker.sock" not in compose
    assert "privileged: true" not in compose
    assert "no-new-privileges:true" in compose
    assert "cap_drop:\n    - ALL" in compose
