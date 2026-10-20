"""ES: Implementa el comando administrativo «validate vinova transfer» para continuidad.

EN: Implements the «validate vinova transfer» management command for continuity.

Contexto existente / Existing context:
Django management command for validate vinova transfer.
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.continuity.transfer import TransferValidationError, validate_installation_transfer


class Command(BaseCommand):
    help = "Valida formato, integridad, compatibilidad y espacio de un paquete .vinova sin importarlo."

    def add_arguments(self, parser):
        parser.add_argument("package")
        parser.add_argument("--destination")
        parser.add_argument("--allow-forward-migration", action="store_true")

    def handle(self, *args, **options):
        try:
            result = validate_installation_transfer(
                Path(options["package"]),
                allow_forward_migration=options["allow_forward_migration"],
                destination_root=Path(options["destination"]) if options["destination"] else None,
            )
        except TransferValidationError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS("Transfer íntegro y compatible."))
        self.stdout.write(f"SHA-256: {result['sha256']}")
