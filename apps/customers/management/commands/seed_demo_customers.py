"""ES: Implementa el comando administrativo «seed demo customers» para clientes.

EN: Implements the «seed demo customers» management command for customers.

Contexto existente / Existing context:
Django management command for seed demo customers.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.branches.models import Branch
from apps.customers.models import Customer, CustomerNote, CustomerVehicleInterest
from apps.vehicles.models import Vehicle


class Command(BaseCommand):
    """ES: Agrupa el componente «command» del dominio de clientes y sus reglas relacionadas. Además, conserva atomicidad y bloqueos explícitos.

    EN: Groups the «command» component and its related rules in the customers domain. It also preserves atomicity and explicit locking.
    """

    help = "Crea clientes demo para validar el módulo comercial de Vinova Pro."

    @transaction.atomic
    def handle(self, *args, **options):
        """ES: Orquesta «seed demo customers» con fallos controlados para clientes.

        EN: Orchestrates «seed demo customers» with controlled failures for customers.
        """

        branch = Branch.objects.filter(is_active=True).first()
        advisor = User.objects.filter(is_active=True, user_roles__role__code__in=["vendedor", "admin_sucursal", "admin_general"]).distinct().first()
        vehicle = Vehicle.objects.filter(is_deleted=False).select_related("brand", "model").first()

        customers = [
            {
                "customer_type": Customer.CustomerType.NATURAL,
                "identification_type": Customer.IdentificationType.CEDULA,
                "identification_number": "0912345678",
                "first_name": "Carlos",
                "last_name": "Mendoza",
                "email": "carlos.mendoza@example.com",
                "phone": "0991112233",
                "whatsapp": "0991112233",
                "city": "Guayaquil",
                "province": "Guayas",
                "source": "Sala de ventas",
                "status": Customer.Status.PROSPECT,
            },
            {
                "customer_type": Customer.CustomerType.COMPANY,
                "identification_type": Customer.IdentificationType.RUC,
                "identification_number": "0999999999001",
                "business_name": "Transporte Andino S.A.",
                "email": "compras@transporteandino.example.com",
                "phone": "042222333",
                "city": "Quito",
                "province": "Pichincha",
                "source": "Web",
                "status": Customer.Status.ACTIVE,
            },
            {
                "customer_type": Customer.CustomerType.NATURAL,
                "identification_type": Customer.IdentificationType.CEDULA,
                "identification_number": "1712345678",
                "first_name": "Ana",
                "last_name": "Paredes",
                "email": "ana.paredes@example.com",
                "phone": "0987654321",
                "whatsapp": "0987654321",
                "city": "Cuenca",
                "province": "Azuay",
                "source": "Referido",
                "status": Customer.Status.VIP,
            },
        ]

        created = 0
        for data in customers:
            customer, was_created = Customer.objects.update_or_create(
                identification_number=data["identification_number"],
                defaults={**data, "assigned_branch": branch, "assigned_advisor": advisor, "created_by": advisor},
            )
            if was_created:
                created += 1
            CustomerNote.objects.get_or_create(
                customer=customer,
                title="Seguimiento inicial",
                defaults={
                    "note_type": CustomerNote.NoteType.GENERAL,
                    "body": "Registro demo para validar la trazabilidad comercial del módulo de clientes.",
                    "created_by": advisor,
                },
            )
            CustomerVehicleInterest.objects.get_or_create(
                customer=customer,
                brand=vehicle.brand.name if vehicle else "GMC",
                model_name=vehicle.model.name if vehicle else "Canyon",
                defaults={
                    "vehicle": vehicle,
                    "budget_min": 25000,
                    "budget_max": 70000,
                    "notes": "Interés demo creado para futuras cotizaciones y reservas.",
                    "created_by": advisor,
                },
            )
        self.stdout.write(self.style.SUCCESS(f"Clientes demo listos. Nuevos creados: {created}."))
