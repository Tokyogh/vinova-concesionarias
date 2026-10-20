"""ES: Implementa el comando administrativo «security review» para seguridad.

EN: Implements the «security review» management command for security center.

Contexto existente / Existing context:
Django management command for security review.
"""

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.security_center.models import ActiveSession, SecurityPolicy, UserSecurityProfile

class Command(BaseCommand):
    help = "Ejecuta una revisión resumida de hardening de Vinova Pro."

    def handle(self, *args, **options):
        policy = SecurityPolicy.current()
        required_without_2fa = sum(1 for p in UserSecurityProfile.objects.select_related("user") if p.is_two_factor_required(policy) and not p.two_factor_enabled)
        self.stdout.write(f"DEBUG={settings.DEBUG}")
        self.stdout.write(f"HTTPS redirect={getattr(settings, 'SECURE_SSL_REDIRECT', False)}")
        self.stdout.write(f"Cookie sesión segura={getattr(settings, 'SESSION_COOKIE_SECURE', False)}")
        self.stdout.write(f"Cookie CSRF segura={getattr(settings, 'CSRF_COOKIE_SECURE', False)}")
        self.stdout.write(f"Cuentas administrativas pendientes de 2FA={required_without_2fa}")
        self.stdout.write(f"Sesiones activas rastreadas={ActiveSession.objects.filter(revoked_at__isnull=True).count()}")
        call_command("check", "--tag", "security")
