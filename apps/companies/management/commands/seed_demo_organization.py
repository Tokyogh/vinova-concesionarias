"""ES: Implementa el comando administrativo «seed demo organization» para empresa.

EN: Implements the «seed demo organization» management command for companies.

Contexto existente / Existing context:
Django management command for seed demo organization.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.branches.models import Branch
from apps.companies.models import Company
from apps.enterprise.services import ensure_default_approval_policies, ensure_public_settings
from apps.sri_integration.selectors import get_or_create_sri_configuration
from apps.sri_integration.models import SriEstablishment, SriSequence


class Command(BaseCommand):
    """Seed an idempotent organization fixture for local demonstration only."""

    help = "Crea una empresa y sucursales demo para probar Vinova Pro localmente."

    @transaction.atomic
    def handle(self, *args, **options):
        """ES: Orquesta «seed demo organization» con fallos controlados para empresa.

        EN: Orchestrates «seed demo organization» with controlled failures for companies.
        """

        company, _ = Company.objects.update_or_create(
            ruc="1799999999001",
            defaults={
                "legal_name": "Vinova Demo Motors S.A.",
                "commercial_name": "Vinova Demo Motors",
                "email": "contacto@vinova.local",
                "phone": "+593 2 000 0000",
                "address": "Dirección demo para desarrollo local",
                "primary_color": "#123b63",
                "secondary_color": "#eef3f8",
                "is_active": True,
            },
        )
        branches = [
            {
                "code": "QUITO-NORTE",
                "name": "Concesionaria Quito Norte",
                "branch_type": Branch.BranchType.DEALERSHIP,
                "city": "Quito",
                "province": "Pichincha",
                "address": "Av. principal demo, Quito",
                "phone": "+593 2 111 1111",
                "email": "quito@vinova.local",
                "description": "Sala de exhibición y atención comercial de la red Vinova.",
                "opening_hours": "Lunes a sábado: 09h00 - 18h00",
                "services": ["Venta de vehículos", "Financiamiento", "Prueba de manejo", "Postventa"],
                "latitude": "-0.180653",
                "longitude": "-78.467834",
                "is_public": True,
                "is_active": True,
            },
            {
                "code": "GYE-CENTRO",
                "name": "Centro de atención Guayaquil",
                "branch_type": Branch.BranchType.SERVICE_CENTER,
                "city": "Guayaquil",
                "province": "Guayas",
                "address": "Av. demo centro, Guayaquil",
                "phone": "+593 4 222 2222",
                "email": "guayaquil@vinova.local",
                "description": "Centro de información, soporte y acompañamiento postventa.",
                "opening_hours": "Lunes a viernes: 08h30 - 17h30",
                "services": ["Atención al cliente", "Soporte postventa", "Garantías"],
                "latitude": "-2.170998",
                "longitude": "-79.922359",
                "is_public": True,
                "is_active": True,
            },
            {
                "code": "ALIADO-DEMO",
                "name": "Institución aliada Vinova",
                "branch_type": Branch.BranchType.AFFILIATED_INSTITUTION,
                "city": "Cuenca",
                "province": "Azuay",
                "address": "Sector institucional demo, Cuenca",
                "phone": "+593 7 444 4444",
                "email": "alianzas@vinova.local",
                "description": "Institución demostrativa afiliada a los programas de la red Vinova.",
                "opening_hours": "Lunes a viernes: 09h00 - 17h00",
                "services": ["Información de convenios", "Asesoría", "Beneficios afiliados"],
                "latitude": "-2.900128",
                "longitude": "-79.005896",
                "is_public": True,
                "is_active": True,
            },
            {
                "code": "BODEGA-CENTRAL",
                "name": "Bodega Central",
                "branch_type": Branch.BranchType.WAREHOUSE,
                "city": "Quito",
                "address": "Zona logística demo",
                "phone": "+593 2 333 3333",
                "email": "bodega@vinova.local",
                "is_public": False,
                "is_active": True,
            },
        ]
        branch_objects = []
        for data in branches:
            branch, _ = Branch.objects.update_or_create(company=company, code=data["code"], defaults=data)
            branch_objects.append(branch)

        public_settings = ensure_public_settings(company)
        public_settings.public_email = public_settings.public_email or "contacto@vinova.local"
        public_settings.public_phone = public_settings.public_phone or "+593 2 000 0000"
        public_settings.whatsapp = public_settings.whatsapp or "+593 99 000 0000"
        public_settings.public_address = public_settings.public_address or "Matriz demo de Vinova Pro"
        public_settings.opening_hours = public_settings.opening_hours or "Lunes a viernes: 09h00 - 18h00"
        public_settings.save()

        sri = get_or_create_sri_configuration(company)
        if not sri.establishments.exists() and branch_objects:
            est = SriEstablishment.objects.create(configuration=sri, establishment_code="001", emission_point_code="001", name="Matriz", branch=branch_objects[0], address=branch_objects[0].address, is_default=True)
            SriSequence.objects.get_or_create(establishment=est, document_type=SriSequence.DocumentType.INVOICE, defaults={"current_number": 0, "start_number": 1})
            SriSequence.objects.get_or_create(establishment=est, document_type=SriSequence.DocumentType.CREDIT_NOTE, defaults={"current_number": 0, "start_number": 1})
        ensure_default_approval_policies(company=company)
        self.stdout.write(self.style.SUCCESS("Empresa, sucursales y control empresarial demo creados."))
