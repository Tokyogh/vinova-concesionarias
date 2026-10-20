"""ES: Implementa el comando administrativo «preflight vinova update» para infraestructura compartida.

EN: Implements the «preflight vinova update» management command for common.

Contexto existente / Existing context:
Django management command for preflight vinova update.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.common.update_manifest import (
    ReleaseManifestError,
    load_release_manifest,
    run_update_preflight,
)
from apps.continuity.models import BackupRecord


class Command(BaseCommand):
    help = "Valida un release local sin desplegarlo ni requerir privilegios del host."

    def add_arguments(self, parser):
        parser.add_argument("manifest")
        parser.add_argument("artifact")
        parser.add_argument("public_key")
        parser.add_argument("--key-id", required=True, help="ID de la clave confiable configurada fuera del manifest.")
        parser.add_argument("--allow-non-postgresql", action="store_true", help="Sólo para QA aislado.")

    def handle(self, *args, **options):
        try:
            manifest = load_release_manifest(Path(options["manifest"]))
            public_key = Path(options["public_key"]).read_bytes()
        except (ReleaseManifestError, OSError) as exc:
            raise CommandError(str(exc)) from exc
        backup = BackupRecord.objects.filter(status=BackupRecord.Status.VERIFIED).order_by("-verified_at").first()
        result = run_update_preflight(
            manifest,
            public_key=public_key,
            trusted_key_id=options["key_id"],
            artifact_path=Path(options["artifact"]),
            backup=backup,
            require_postgresql=not options["allow_non_postgresql"],
        )
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
        if not result["ready"]:
            raise CommandError("Preflight inválido; el despliegue debe permanecer detenido.")
