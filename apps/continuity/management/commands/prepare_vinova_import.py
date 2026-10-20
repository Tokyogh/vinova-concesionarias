"""ES: Implementa el comando administrativo «prepare vinova import» para continuidad.

EN: Implements the «prepare vinova import» management command for continuity.

Contexto existente / Existing context:
Django management command for prepare vinova import.
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.continuity.transfer import TransferValidationError, prepare_installation_import


class Command(BaseCommand):
    help = "Prepara un .vinova en un directorio vacío; no restaura ni reemplaza la instalación."

    def add_arguments(self, parser):
        parser.add_argument("package")
        parser.add_argument("--destination", required=True)
        parser.add_argument("--confirm", default="")
        parser.add_argument("--allow-forward-migration", action="store_true")

    def handle(self, *args, **options):
        if options["confirm"] != "PREPARE_IMPORT":
            raise CommandError("Usa --confirm PREPARE_IMPORT para preparar la importación.")
        try:
            result = prepare_installation_import(
                Path(options["package"]),
                Path(options["destination"]),
                allow_forward_migration=options["allow_forward_migration"],
            )
        except TransferValidationError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS("Transfer extraído en un directorio aislado."))
        self.stdout.write(f"SHA-256: {result['sha256']}")
        self.stdout.write("Reaprovisione secretos y ejecute la restauración/migración fuera del proceso web.")
