"""ES: Audita datos de contacto heredados sin modificarlos ni exponerlos.

EN: Audits legacy contact data without modifying or exposing it.
"""

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.common.validators import validate_phone_number


class Command(BaseCommand):
    """ES: Informa identificadores internos con teléfonos inválidos.

    EN: Reports internal identifiers for records with invalid phone values.
    """

    help = "Audita teléfonos y WhatsApp heredados; es una operación de solo lectura."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fail-on-invalid",
            action="store_true",
            help="Devuelve error si se encuentran registros inválidos.",
        )

    def handle(self, *args, **options):
        # ES: Las importaciones tardías mantienen liviano el arranque del comando.
        # EN: Lazy imports keep command startup lightweight.
        from django.contrib.auth import get_user_model

        from apps.branches.models import Branch
        from apps.companies.models import Company
        from apps.customers.models import Customer
        from apps.enterprise.models import CompanyPublicSettings
        from apps.leads.models import Lead
        from apps.privacy.models import DataSubjectRequest

        targets = (
            (get_user_model(), ("phone",)),
            (Customer, ("phone", "whatsapp")),
            (Lead, ("phone", "whatsapp")),
            (Branch, ("phone",)),
            (Company, ("phone",)),
            (CompanyPublicSettings, ("public_phone", "whatsapp")),
            (DataSubjectRequest, ("requester_phone",)),
        )
        invalid = []
        inspected = 0
        for model, fields in targets:
            rows = model._default_manager.values_list("pk", *fields).iterator(chunk_size=500)
            for row in rows:
                pk, *values = row
                for field, value in zip(fields, values):
                    if not value:
                        continue
                    inspected += 1
                    try:
                        validate_phone_number(value)
                    except ValidationError:
                        invalid.append((model._meta.label, pk, field))

        self.stdout.write(f"Contactos inspeccionados: {inspected}")
        self.stdout.write(f"Campos inválidos: {len(invalid)}")
        for label, pk, field in invalid:
            self.stdout.write(f"- {label} pk={pk} campo={field}")
        if invalid and options["fail_on_invalid"]:
            raise CommandError("Existen contactos heredados inválidos; no se modificó ningún registro.")
