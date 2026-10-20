"""ES: Implementa el comando administrativo «verify vinova backup» para continuidad.

EN: Implements the «verify vinova backup» management command for continuity.

Contexto existente / Existing context:
Django management command for verify vinova backup.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.continuity.models import BackupRecord
from apps.continuity.services import verify_backup


class Command(BaseCommand):
    help = "Verifica el archivo, hash y manifiesto de un backup de Vinova Pro."

    def add_arguments(self, parser):
        parser.add_argument("backup_id", help="UUID público del backup.")

    def handle(self, *args, **options):
        try:
            record = BackupRecord.objects.get(public_id=options["backup_id"])
        except (BackupRecord.DoesNotExist, ValueError) as exc:
            raise CommandError("Backup no encontrado.") from exc
        result = verify_backup(record)
        if not result["valid"]:
            raise CommandError(result["reason"])
        self.stdout.write(self.style.SUCCESS("Backup íntegro y verificable."))
        self.stdout.write(f"SHA-256: {result['sha256']}")
        self.stdout.write(
            f"Restore compatibility: {'compatible' if result['compatible'] else result['reason']}"
        )
