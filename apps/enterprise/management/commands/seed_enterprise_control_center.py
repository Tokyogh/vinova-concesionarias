"""ES: Implementa el comando administrativo «seed enterprise control center» para configuración empresarial.

EN: Implements the «seed enterprise control center» management command for enterprise.

Contexto existente / Existing context:
Django management command for seed enterprise control center.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.enterprise.selectors import get_primary_company
from apps.enterprise.services import ensure_default_approval_policies, ensure_public_settings
from apps.sri_integration.selectors import get_or_create_sri_configuration


class Command(BaseCommand):
    help = "Crea configuración base del Centro Empresarial v0.14 para la empresa principal."

    @transaction.atomic
    def handle(self, *args, **options):
        company = get_primary_company()
        if not company:
            self.stdout.write(self.style.WARNING("No existe empresa. Ejecuta seed_demo_organization o crea una empresa primero."))
            return
        ensure_public_settings(company)
        get_or_create_sri_configuration(company)
        ensure_default_approval_policies(company=company)
        self.stdout.write(self.style.SUCCESS("Centro empresarial base listo."))
