"""ES: Implementa el comando administrativo «prepare vinova restore» para continuidad.

EN: Implements the «prepare vinova restore» management command for continuity.

Contexto existente / Existing context:
Django management command for prepare vinova restore.
"""

import shutil
import tarfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.continuity.models import BackupRecord
from apps.continuity.services import backup_archive_path, verify_backup


class Command(BaseCommand):
    help = "Extrae un backup verificado en un directorio aislado. No sobrescribe producción ni restaura la base automáticamente."

    def add_arguments(self, parser):
        parser.add_argument("backup_id")
        parser.add_argument("--destination", required=True)
        parser.add_argument("--confirm", default="", help="Debe ser exactamente PREPARE_RESTORE.")
        parser.add_argument("--allow-forward-migration", action="store_true")

    def handle(self, *args, **options):
        if options["confirm"] != "PREPARE_RESTORE":
            raise CommandError("Usa --confirm PREPARE_RESTORE para evitar extracciones accidentales.")
        try:
            record = BackupRecord.objects.get(public_id=options["backup_id"])
        except (BackupRecord.DoesNotExist, ValueError) as exc:
            raise CommandError("Backup no encontrado.") from exc
        result = verify_backup(record, allow_forward_migration=options["allow_forward_migration"])
        if not result["valid"]:
            raise CommandError(result["reason"])
        if not result["compatible"]:
            raise CommandError(result["reason"])
        destination = Path(options["destination"]).resolve()
        destination.mkdir(parents=True, exist_ok=True)
        if any(destination.iterdir()):
            raise CommandError("El directorio de destino debe estar vacío.")
        required_bytes = sum(item["size_bytes"] for item in result["manifest"].get("inventory", []))
        if shutil.disk_usage(destination).free < required_bytes * 2:
            raise CommandError("Espacio libre insuficiente para preparar y validar la restauración.")
        with tarfile.open(backup_archive_path(record), "r:gz") as archive:
            archive.extractall(destination, filter="data")
        self.stdout.write(self.style.SUCCESS(f"Backup extraído en entorno aislado: {destination}"))
        self.stdout.write("Revise manifest.json y restaure la base con herramientas PostgreSQL fuera de producción.")
