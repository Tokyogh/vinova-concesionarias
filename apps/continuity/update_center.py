"""ES: Este módulo implementa el componente update center para el dominio de continuidad.

EN: This module implements the update center component for the continuity domain.

Contexto existente / Existing context:
Update center support for the continuity domain.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings

from apps.common.health import dependency_status
from apps.common.lifecycle import installation_lifecycle_state
from apps.common.update_manifest import ReleaseManifestError, load_release_manifest, run_update_preflight
from apps.continuity.models import BackupRecord


AGENT_STATES = {"idle", "checking", "preflight", "maintenance", "deploying", "healthy", "failed"}
AGENT_STATE_LABELS = {
    "idle": "En espera",
    "checking": "Comprobando",
    "preflight": "Preflight",
    "maintenance": "Mantenimiento",
    "deploying": "Desplegando",
    "healthy": "Operativo",
    "failed": "Fallido",
}


def update_agent_status() -> dict:
    configured = str(settings.VINOVA_UPDATE_AGENT_STATUS_FILE or "").strip()
    if not configured:
        return {"connected": False, "state": "unavailable", "message": "Update Agent no configurado."}
    path = Path(configured)
    try:
        if not path.is_file() or path.stat().st_size > 128 * 1024:
            raise ValueError("Archivo de estado ausente o demasiado grande.")
        payload = json.loads(path.read_text(encoding="utf-8"))
        state = payload.get("state")
        if state not in AGENT_STATES:
            raise ValueError("Estado de agente no reconocido.")
        return {
            "connected": True,
            "state": state,
            "state_label": AGENT_STATE_LABELS[state],
            "message": str(payload.get("message") or "")[:300],
            "target_version": str(payload.get("target_version") or "")[:32],
            "updated_at": str(payload.get("updated_at") or "")[:64],
        }
    except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return {
            "connected": False,
            "state": "invalid",
            "state_label": "Estado inválido",
            "message": "El estado publicado por Update Agent no es válido o no puede leerse.",
        }


def configured_release_status(*, health: dict[str, tuple[bool, str]], backup) -> dict:
    values = {
        "manifest": str(settings.VINOVA_RELEASE_MANIFEST_PATH or "").strip(),
        "artifact": str(settings.VINOVA_RELEASE_ARTIFACT_PATH or "").strip(),
        "public_key": str(settings.VINOVA_RELEASE_PUBLIC_KEY_PATH or "").strip(),
        "key_id": str(settings.VINOVA_RELEASE_TRUSTED_KEY_ID or "").strip(),
    }
    if not all(values.values()):
        return {
            "configured": False,
            "ready": False,
            "message": "No hay un release real configurado para preflight.",
            "checks": [],
        }
    try:
        manifest = load_release_manifest(Path(values["manifest"]))
        preflight = run_update_preflight(
            manifest,
            public_key=Path(values["public_key"]).read_bytes(),
            trusted_key_id=values["key_id"],
            artifact_path=Path(values["artifact"]),
            backup=backup,
            dependency_health={name: value[0] for name, value in health.items()},
        )
    except (OSError, ReleaseManifestError):
        return {
            "configured": True,
            "ready": False,
            "message": "El release configurado no es válido o no puede verificarse.",
            "checks": [],
        }
    return {
        "configured": True,
        "channel": manifest["channel"],
        "published_at": manifest["published_at"],
        "message": "Preflight listo." if preflight["ready"] else "Preflight bloqueado.",
        **preflight,
    }


def update_center_context() -> dict:
    lifecycle = installation_lifecycle_state()
    backup = BackupRecord.objects.filter(status=BackupRecord.Status.VERIFIED).order_by("-verified_at").first()
    health = dependency_status()
    return {
        "lifecycle": lifecycle,
        "latest_verified_backup": backup,
        "health_checks": [
            {"name": name, "ok": ok, "detail": detail} for name, (ok, detail) in sorted(health.items())
        ],
        "all_healthy": all(ok for ok, _detail in health.values()),
        "agent_status": update_agent_status(),
        "release_status": configured_release_status(health=health, backup=backup),
    }
