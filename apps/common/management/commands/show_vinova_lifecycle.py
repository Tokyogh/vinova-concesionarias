"""ES: Implementa el comando administrativo «show vinova lifecycle» para infraestructura compartida.

EN: Implements the «show vinova lifecycle» management command for common.

Contexto existente / Existing context:
Django management command for show vinova lifecycle.
"""

import json

from django.core.management.base import BaseCommand

from apps.common.lifecycle import installation_lifecycle_state


class Command(BaseCommand):
    help = "Muestra versión de producto, ledger de migraciones y formatos de lifecycle por separado."

    def add_arguments(self, parser):
        parser.add_argument("--database", default="default", help="Alias de base de datos de Django.")
        parser.add_argument("--json", action="store_true", help="Emite un documento JSON estable.")

    def handle(self, *args, **options):
        state = installation_lifecycle_state(using=options["database"])
        if options["json"]:
            self.stdout.write(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True))
            return
        migration = state["database_migration_state"]
        self.stdout.write(f"Product version: {state['product_version']}")
        self.stdout.write(
            f"Migration state: {'current' if migration['is_current'] else 'pending'} "
            f"({migration['applied_count']} applied, {migration['pending_count']} pending)"
        )
        self.stdout.write(f"Migration fingerprint: {migration['fingerprint_sha256']}")
        self.stdout.write(f"Backup format: {state['backup_format_version']}")
        self.stdout.write(f"Transfer format: {state['transfer_format_version']}")
