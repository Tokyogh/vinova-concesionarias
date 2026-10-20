"""ES: Implementa el comando administrativo «export vinova installation» para continuidad.

EN: Implements the «export vinova installation» management command for continuity.

Contexto existente / Existing context:
Django management command for export vinova installation.
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.continuity.transfer import TransferValidationError, export_installation_transfer


class Command(BaseCommand):
    help = "Exporta estado portable de una instalación a un paquete .vinova sin secretos ni código fuente."

    def add_arguments(self, parser):
        parser.add_argument("destination")

    def handle(self, *args, **options):
        try:
            result = export_installation_transfer(Path(options["destination"]))
        except (TransferValidationError, RuntimeError, OSError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Transfer creado: {result['path']}"))
        self.stdout.write(f"SHA-256: {result['sha256']}")
