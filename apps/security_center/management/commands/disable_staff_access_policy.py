"""ES: Implementa el comando administrativo «disable staff access policy» para seguridad.

EN: Implements the «disable staff access policy» management command for security center.

Contexto existente / Existing context:
Desactiva de emergencia la restricción Staff desde una consola privilegiada.

Emergency-disable Staff access enforcement from a privileged console.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.audit.services import audit_log
from apps.security_center.models import SecurityPolicy


class Command(BaseCommand):
    help = "Desactiva la política adaptativa Staff; requiere confirmación literal."

    def add_arguments(self, parser):
        parser.add_argument("--confirm", default="")

    def handle(self, *args, **options):
        if options["confirm"] != "DISABLE-STAFF-ACCESS":
            raise CommandError("Usa --confirm DISABLE-STAFF-ACCESS para confirmar la recuperación.")
        policy = SecurityPolicy.current()
        previous = policy.staff_access_mode
        policy.staff_access_mode = SecurityPolicy.StaffAccessMode.OFF
        policy.save(update_fields=["staff_access_mode", "updated_at"])
        audit_log(
            user=None,
            action="security.staff_access.emergency_disabled",
            target=policy,
            before={"staff_access_mode": previous},
            after={"staff_access_mode": policy.staff_access_mode},
        )
        self.stdout.write(self.style.SUCCESS("La restricción Staff quedó desactivada y auditada."))
