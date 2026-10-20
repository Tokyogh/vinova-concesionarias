"""ES: Implementa el comando administrativo «create vinova backup» para continuidad.

EN: Implements the «create vinova backup» management command for continuity.

Contexto existente / Existing context:
Django management command for create vinova backup.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.continuity.models import BackupRecord
from apps.continuity.services import create_backup_record, execute_backup


class Command(BaseCommand):
    help = "Crea un backup verificable de Vinova Pro en private/backups/."

    def add_arguments(self, parser):
        parser.add_argument(
            "--type",
            choices=[value for value, _ in BackupRecord.BackupType.choices],
            default=BackupRecord.BackupType.FULL,
        )
        parser.add_argument("--username", default="", help="Usuario que quedará registrado como responsable.")
        parser.add_argument("--notes", default="")

    def handle(self, *args, **options):
        actor = None
        if options["username"]:
            actor = get_user_model().objects.filter(username=options["username"]).first()
            if not actor:
                raise CommandError("No existe el usuario indicado.")
        record = create_backup_record(
            actor=actor,
            backup_type=options["type"],
            notes=options["notes"],
            execution_mode=BackupRecord.ExecutionMode.COMMAND,
        )
        execute_backup(record)
        record.refresh_from_db()
        if record.status == BackupRecord.Status.FAILED:
            raise CommandError(record.error_message)
        self.stdout.write(self.style.SUCCESS(f"Backup creado: {record.filename}"))
        self.stdout.write(f"SHA-256: {record.sha256}")
