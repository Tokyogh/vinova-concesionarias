"""ES: Implementa el comando administrativo «seed demo leads» para CRM y leads.

EN: Implements the «seed demo leads» management command for leads.

Contexto existente / Existing context:
Django management command for seed demo leads.
"""

from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.analytics.models import VehicleInteraction
from apps.branches.models import Branch
from apps.leads.models import Lead, LeadActivity
from apps.leads.services import refresh_lead_score
from apps.vehicles.models import Vehicle


class Command(BaseCommand):
    """ES: Agrupa el componente «command» del dominio de CRM y leads y sus reglas relacionadas. Además, conserva atomicidad y bloqueos explícitos.

    EN: Groups the «command» component and its related rules in the leads domain. It also preserves atomicity and explicit locking.
    """

    help = "Crea leads, actividades e interacciones demo para validar CRM y analítica v0.17."

    @transaction.atomic
    def handle(self, *args, **options):
        """ES: Orquesta «seed demo leads» con fallos controlados para CRM y leads.

        EN: Orchestrates «seed demo leads» with controlled failures for leads.
        """

        branch = Branch.objects.filter(is_active=True).first()
        vehicle = Vehicle.objects.filter(is_deleted=False).select_related("brand", "model", "branch").first()
        advisor = User.objects.filter(is_active=True, is_staff=True).first() or User.objects.filter(is_active=True).first()
        if branch is None and vehicle is not None:
            branch = vehicle.branch
        if branch is None:
            self.stdout.write(self.style.WARNING("No hay sucursales activas. Ejecuta seed_demo_organization antes de seed_demo_leads."))
            return

        demo_rows = [
            ("Andrea Molina", "andrea.demo@example.com", "0991000001", "Quito", Lead.RequestType.QUOTE, Lead.Status.NEW, Lead.Priority.HIGH, Lead.Source.WEB_CATALOG),
            ("Carlos Vera", "carlos.demo@example.com", "0991000002", "Guayaquil", Lead.RequestType.TEST_DRIVE, Lead.Status.CONTACTED, Lead.Priority.HIGH, Lead.Source.WEBSITE),
            ("Diana Flores", "diana.demo@example.com", "0991000003", "Cuenca", Lead.RequestType.INFORMATION, Lead.Status.INTERESTED, Lead.Priority.MEDIUM, Lead.Source.REFERRAL),
            ("Esteban Ruiz", "esteban.demo@example.com", "0991000004", "Manta", Lead.RequestType.FINANCING, Lead.Status.NEGOTIATION, Lead.Priority.URGENT, Lead.Source.SHOWROOM),
            ("Fernanda Paz", "fernanda.demo@example.com", "0991000005", "Quito", Lead.RequestType.QUOTE, Lead.Status.WON, Lead.Priority.HIGH, Lead.Source.WEB_CATALOG),
        ]
        created = 0
        now = timezone.now()
        for index, (name, email, phone, city, request_type, status, priority, source) in enumerate(demo_rows):
            lead, was_created = Lead.objects.get_or_create(
                email=email,
                defaults={
                    "full_name": name,
                    "phone": phone,
                    "whatsapp": phone,
                    "city": city,
                    "province": "Pichincha" if city == "Quito" else "",
                    "request_type": request_type,
                    "status": status,
                    "priority": priority,
                    "source": source,
                    "vehicle": vehicle,
                    "branch": branch,
                    "assigned_advisor": advisor,
                    "message": "Registro demostrativo del CRM Vinova Pro v0.17.",
                    "consent_data_processing": source in {Lead.Source.WEB_CATALOG, Lead.Source.WEBSITE},
                    "next_follow_up_at": None if status in {Lead.Status.WON, Lead.Status.LOST} else now + timedelta(days=index - 1),
                    "closed_at": now if status == Lead.Status.WON else None,
                    "created_by": advisor,
                },
            )
            if was_created:
                created += 1
                refresh_lead_score(lead)
                LeadActivity.objects.create(
                    lead=lead,
                    activity_type=LeadActivity.ActivityType.SYSTEM,
                    title="Lead demo creado",
                    detail="Datos demostrativos para revisar pipeline y analítica.",
                    created_by=advisor,
                )
                if vehicle:
                    VehicleInteraction.objects.create(
                        event_type=VehicleInteraction.EventType.LEAD_SUBMITTED,
                        vehicle=vehicle,
                        lead=lead,
                        branch=branch,
                        city=city,
                        metadata={"demo": True},
                    )
        self.stdout.write(self.style.SUCCESS(f"CRM demo listo. Leads nuevos: {created}; total demo: {len(demo_rows)}."))
