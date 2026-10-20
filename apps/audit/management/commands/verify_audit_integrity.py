"""ES: Implementa el comando administrativo «verify audit integrity» para auditoría.

EN: Implements the «verify audit integrity» management command for audit.

Contexto existente / Existing context:
Django management command for verify audit integrity.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.audit.services import verify_audit_chain


class Command(BaseCommand):
    help = "Verifica la cadena SHA-256 de todos los registros de auditoría."

    def handle(self, *args, **options):
        result = verify_audit_chain(strict_links=True)
        self.stdout.write(f"Eventos revisados: {result['checked']}")
        self.stdout.write(f"Último hash: {result['last_hash'] or 'Sin registros'}")
        if not result["valid"]:
            for issue in result["issues"][:20]:
                self.stderr.write(
                    f"Inconsistencia: {issue['event_id']} · {issue['action']} · "
                    f"hash={issue.get('invalid_hash')} enlace={issue.get('invalid_link')}"
                )
            raise CommandError("La cadena de auditoría presenta inconsistencias.")
        self.stdout.write(self.style.SUCCESS("Cadena de auditoría íntegra."))
