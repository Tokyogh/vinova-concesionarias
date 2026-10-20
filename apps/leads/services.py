"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de CRM y leads.

EN: This module implements business services and transactional effects for the leads domain.

Contexto existente / Existing context:
Transactional business services for the leads domain.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.scopes import accessible_branch_ids
from apps.analytics.models import VehicleInteraction
from apps.analytics.services import record_vehicle_interaction, request_identity
from apps.audit.services import audit_log
from apps.common.db_locks import acquire_transaction_advisory_lock
from apps.common.normalization import normalize_email, normalize_phone
from apps.customers.models import Customer, CustomerNote, CustomerVehicleInterest
from apps.leads.models import Lead, LeadActivity, TestDrive
from apps.sales.models import SaleRecord
from apps.sales.services import create_sale_from_data


def lead_snapshot(lead: Lead) -> dict:
    return {
        "code": lead.code,
        "status": lead.status,
        "priority": lead.priority,
        "source": lead.source,
        "request_type": lead.request_type,
        "full_name": lead.full_name,
        "email": lead.email,
        "phone": lead.phone,
        "city": lead.city,
        "branch": lead.branch_id,
        "advisor": lead.assigned_advisor_id,
        "vehicle": lead.vehicle_id,
        "customer": lead.customer_id,
        "sale": lead.linked_sale_id,
        "score": lead.score,
        "next_follow_up_at": lead.next_follow_up_at.isoformat() if lead.next_follow_up_at else "",
    }


def _require_branch_access(*, actor, permission_code: str, branch) -> None:
    branch_ids = accessible_branch_ids(actor, permission_codes=(permission_code,))
    if branch_ids is not None and (branch is None or branch.pk not in branch_ids):
        raise ValidationError("No tienes permiso para operar leads en esta sucursal.")


def _validate_advisor_branch(*, advisor, branch) -> None:
    if advisor is None or branch is None:
        return
    if advisor.is_superuser:
        return
    if not advisor.active_role_assignments().filter(Q(branch=branch) | Q(branch__isnull=True)).exists():
        raise ValidationError("El asesor no tiene una asignación activa para esta sucursal.")


def _validate_lead_relations(lead: Lead) -> None:
    if lead.customer_id and lead.branch_id and lead.customer.assigned_branch_id not in (None, lead.branch_id):
        raise ValidationError("El cliente pertenece a otra sucursal.")
    if lead.vehicle_id and lead.branch_id and lead.vehicle.branch_id not in (None, lead.branch_id):
        raise ValidationError("El vehículo pertenece a otra sucursal.")


def _persist_new_internal_lead(*, actor, lead: Lead) -> Lead:
    lead.created_by = actor
    if lead.assigned_advisor_id is None and actor.has_perm_code("leads.manage"):
        lead.assigned_advisor = actor
    if lead.branch_id is None:
        lead.branch = getattr(lead.vehicle, "branch", None) or getattr(actor, "branch", None)
    _require_branch_access(actor=actor, permission_code="leads.manage", branch=lead.branch)
    _validate_advisor_branch(advisor=lead.assigned_advisor, branch=lead.branch)
    _validate_lead_relations(lead)
    lead.full_clean()
    lead.save()
    refresh_lead_score(lead)
    add_system_activity(lead=lead, title="Lead creado manualmente", actor=actor)
    audit_log(user=actor, action="leads.create", target=lead, after=lead_snapshot(lead))
    return lead


def calculate_lead_score(lead: Lead) -> int:
    score = 10
    score += 8 if lead.email else 0
    score += 10 if (lead.phone or lead.whatsapp) else 0
    score += 6 if lead.city else 0
    score += 18 if lead.vehicle_id else 0
    score += 8 if (lead.interested_brand or lead.interested_model) else 0
    score += 10 if (lead.budget_min is not None or lead.budget_max is not None) else 0
    score += 8 if lead.expected_purchase_date else 0
    score += {Lead.RequestType.INFORMATION: 4, Lead.RequestType.QUOTE: 12, Lead.RequestType.TEST_DRIVE: 15, Lead.RequestType.FINANCING: 10, Lead.RequestType.OTHER: 2}.get(lead.request_type, 0)
    score += {Lead.Status.NEW: 0, Lead.Status.CONTACTED: 5, Lead.Status.INTERESTED: 10, Lead.Status.QUOTED: 14, Lead.Status.TEST_DRIVE: 16, Lead.Status.NEGOTIATION: 20, Lead.Status.WON: 25, Lead.Status.LOST: -10}.get(lead.status, 0)
    return max(0, min(score, 100))


def refresh_lead_score(lead: Lead, *, save=True) -> int:
    lead.score = calculate_lead_score(lead)
    if lead.score >= 80 and lead.priority not in {Lead.Priority.URGENT}:
        lead.priority = Lead.Priority.HIGH
    elif lead.score < 35 and lead.priority == Lead.Priority.MEDIUM:
        lead.priority = Lead.Priority.LOW
    if save:
        lead.save(update_fields=["score", "priority", "updated_at"])
    return lead.score


def add_system_activity(*, lead: Lead, title: str, detail: str = "", activity_type=LeadActivity.ActivityType.SYSTEM, actor=None, **extra):
    return LeadActivity.objects.create(
        lead=lead,
        activity_type=activity_type,
        title=title,
        detail=detail,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        **extra,
    )


@transaction.atomic
def create_public_lead(*, request, form, vehicle=None) -> Lead:
    lead = form.save(commit=False)
    lead.vehicle = vehicle
    lead.branch = getattr(vehicle, "branch", None)
    lead.source = Lead.Source.WEB_CATALOG if vehicle else Lead.Source.WEBSITE
    identity = request_identity(request)
    lead.session_hash = identity["session_hash"]
    lead.ip_hash = identity["ip_hash"]
    lead.source_url = identity["source_url"]
    lead.referrer = identity["referrer"]
    lead.utm_source = request.GET.get("utm_source", request.POST.get("utm_source", ""))[:120]
    lead.utm_medium = request.GET.get("utm_medium", request.POST.get("utm_medium", ""))[:120]
    lead.utm_campaign = request.GET.get("utm_campaign", request.POST.get("utm_campaign", ""))[:160]
    lead.full_clean()
    lead.save()
    refresh_lead_score(lead)
    add_system_activity(
        lead=lead,
        title="Solicitud recibida desde el sitio público",
        detail=lead.message,
        activity_type=LeadActivity.ActivityType.SYSTEM,
    )
    event_type = {
        Lead.RequestType.QUOTE: VehicleInteraction.EventType.QUOTE_REQUEST,
        Lead.RequestType.TEST_DRIVE: VehicleInteraction.EventType.TEST_DRIVE_REQUEST,
    }.get(lead.request_type, VehicleInteraction.EventType.LEAD_SUBMITTED)
    record_vehicle_interaction(request=request, event_type=event_type, vehicle=vehicle, lead=lead, city=lead.city, province=lead.province)
    audit_log(user=None, action="leads.public.create", target=lead, after=lead_snapshot(lead), metadata={"privacy": "ip/session stored as SHA-256 hashes"})
    return lead


@transaction.atomic
def create_internal_lead(*, actor, form) -> Lead:
    return _persist_new_internal_lead(actor=actor, lead=form.save(commit=False))


@transaction.atomic
def create_internal_lead_from_data(*, actor, validated_data: dict) -> Lead:
    return _persist_new_internal_lead(actor=actor, lead=Lead(**validated_data))


@transaction.atomic
def update_lead(*, actor, lead: Lead, form) -> Lead:
    before = lead_snapshot(lead)
    lead = form.save(commit=False)
    if lead.branch_id is None:
        lead.branch = getattr(lead.vehicle, "branch", None) or getattr(actor, "branch", None)
    _require_branch_access(actor=actor, permission_code="leads.manage", branch=lead.branch)
    _validate_advisor_branch(advisor=lead.assigned_advisor, branch=lead.branch)
    _validate_lead_relations(lead)
    if lead.status in {Lead.Status.WON, Lead.Status.LOST} and not lead.closed_at:
        lead.closed_at = timezone.now()
    elif lead.status not in {Lead.Status.WON, Lead.Status.LOST}:
        lead.closed_at = None
    lead.full_clean()
    lead.save()
    refresh_lead_score(lead)
    audit_log(user=actor, action="leads.update", target=lead, before=before, after=lead_snapshot(lead))
    return lead


@transaction.atomic
def change_lead_status(*, actor, lead: Lead, status: str, note: str = "", lost_reason: str = "", next_follow_up_at=None) -> Lead:
    previous = lead.status
    if previous == status and not next_follow_up_at:
        return lead
    before = lead_snapshot(lead)
    lead.status = status
    lead.lost_reason = lost_reason.strip() if status == Lead.Status.LOST else ""
    lead.next_follow_up_at = next_follow_up_at
    if status in {Lead.Status.WON, Lead.Status.LOST}:
        lead.closed_at = timezone.now()
        lead.next_follow_up_at = None
    else:
        lead.closed_at = None
    if status == Lead.Status.CONTACTED:
        lead.last_contact_at = timezone.now()
    lead.full_clean()
    lead.save()
    refresh_lead_score(lead)
    LeadActivity.objects.create(
        lead=lead,
        activity_type=LeadActivity.ActivityType.STATUS,
        title=f"Estado: {lead.get_status_display()}",
        detail=note or lead.lost_reason,
        previous_status=previous,
        new_status=status,
        created_by=actor,
    )
    audit_log(user=actor, action="leads.status_change", target=lead, before=before, after=lead_snapshot(lead))
    return lead


@transaction.atomic
def add_lead_activity(*, actor, lead: Lead, form) -> LeadActivity:
    activity = form.save(commit=False)
    activity.lead = lead
    return _persist_lead_activity(actor=actor, activity=activity)


def _persist_lead_activity(*, actor, activity: LeadActivity) -> LeadActivity:
    lead = activity.lead
    activity.created_by = actor
    activity.full_clean()
    activity.save()
    if activity.completed_at or activity.activity_type in {LeadActivity.ActivityType.CALL, LeadActivity.ActivityType.EMAIL, LeadActivity.ActivityType.WHATSAPP, LeadActivity.ActivityType.VISIT}:
        lead.last_contact_at = activity.completed_at or timezone.now()
    if activity.scheduled_for:
        lead.next_follow_up_at = activity.scheduled_for
    lead.save(update_fields=["last_contact_at", "next_follow_up_at", "updated_at"])
    audit_log(user=actor, action="leads.activity.create", target=lead, after={"activity": activity.activity_type, "title": activity.title, "scheduled_for": str(activity.scheduled_for or "")})
    return activity


@transaction.atomic
def add_lead_activity_from_data(*, actor, validated_data: dict) -> LeadActivity:
    return _persist_lead_activity(actor=actor, activity=LeadActivity(**validated_data))


@transaction.atomic
def assign_lead(*, actor, lead: Lead, branch=None, advisor=None, note: str = "") -> Lead:
    _require_branch_access(actor=actor, permission_code="leads.assign", branch=branch)
    _validate_advisor_branch(advisor=advisor, branch=branch)
    before = {"branch": lead.branch_id, "advisor": lead.assigned_advisor_id}
    lead.branch = branch
    lead.assigned_advisor = advisor
    lead.save(update_fields=["branch", "assigned_advisor", "updated_at"])
    LeadActivity.objects.create(
        lead=lead,
        activity_type=LeadActivity.ActivityType.ASSIGNMENT,
        title="Lead reasignado",
        detail=note,
        created_by=actor,
        metadata={"branch_id": lead.branch_id, "advisor_id": lead.assigned_advisor_id},
    )
    audit_log(user=actor, action="leads.assign", target=lead, before=before, after={"branch": lead.branch_id, "advisor": lead.assigned_advisor_id})
    return lead


@transaction.atomic
def schedule_test_drive(*, actor, lead: Lead, form) -> TestDrive:
    test_drive = form.save(commit=False)
    test_drive.lead = lead
    return _persist_test_drive(actor=actor, test_drive=test_drive)


def _persist_test_drive(*, actor, test_drive: TestDrive) -> TestDrive:
    lead = test_drive.lead
    test_drive.created_by = actor
    if test_drive.advisor_id is None:
        test_drive.advisor = lead.assigned_advisor or actor
    _require_branch_access(actor=actor, permission_code="leads.manage", branch=test_drive.branch)
    _validate_advisor_branch(advisor=test_drive.advisor, branch=test_drive.branch)
    test_drive.full_clean()
    test_drive.save()
    previous = lead.status
    lead.status = Lead.Status.TEST_DRIVE
    lead.vehicle = test_drive.vehicle
    lead.branch = test_drive.branch
    lead.assigned_advisor = test_drive.advisor
    lead.next_follow_up_at = test_drive.starts_at
    lead.save(update_fields=["status", "vehicle", "branch", "assigned_advisor", "next_follow_up_at", "updated_at"])
    refresh_lead_score(lead)
    LeadActivity.objects.create(
        lead=lead,
        activity_type=LeadActivity.ActivityType.TEST_DRIVE,
        title="Test drive agendado",
        detail=test_drive.notes,
        previous_status=previous,
        new_status=lead.status,
        scheduled_for=test_drive.starts_at,
        created_by=actor,
        metadata={"test_drive_id": test_drive.pk, "vehicle_id": test_drive.vehicle_id},
    )
    audit_log(user=actor, action="leads.test_drive.schedule", target=lead, after={"test_drive": test_drive.pk, "starts_at": test_drive.starts_at.isoformat()})
    return test_drive


@transaction.atomic
def schedule_test_drive_from_data(*, actor, validated_data: dict) -> TestDrive:
    return _persist_test_drive(actor=actor, test_drive=TestDrive(**validated_data))


def _locked_lead(lead: Lead) -> Lead:
    return Lead.objects.select_for_update().get(pk=lead.pk, is_deleted=False)


def _lock_customer_identities(lead: Lead) -> None:
    identities = set()
    email = normalize_email(lead.email)
    if email:
        identities.add(f"email:{email}")
    for value in (lead.phone, lead.whatsapp):
        phone = normalize_phone(value)
        if phone:
            identities.add(f"phone:{phone}")
    for identity in sorted(identities):
        acquire_transaction_advisory_lock(namespace="customer-identity", value=identity)


def _matching_customer_for_lead(lead: Lead) -> Customer | None:
    identity_filter = Q()
    if lead.email:
        identity_filter |= Q(email__iexact=normalize_email(lead.email))
    contacts = {normalize_phone(value) for value in (lead.phone, lead.whatsapp) if normalize_phone(value)}
    if contacts:
        identity_filter |= Q(phone__in=contacts) | Q(whatsapp__in=contacts)
    if not identity_filter:
        return None
    matches = list(Customer.objects.filter(identity_filter, is_deleted=False).order_by("pk")[:2])
    if len(matches) > 1:
        raise ValidationError(
            "La identidad del lead coincide con varios clientes. Revisa los datos antes de convertirlo."
        )
    customer = matches[0] if matches else None
    if (
        customer is not None
        and lead.branch_id
        and customer.assigned_branch_id not in (None, lead.branch_id)
    ):
        raise ValidationError("El cliente coincidente pertenece a otra sucursal.")
    return customer


def _convert_locked_lead_to_customer(*, actor, lead: Lead) -> Customer:
    if lead.customer_id:
        return lead.customer
    _lock_customer_identities(lead)
    customer = _matching_customer_for_lead(lead)
    if customer is None:
        names = lead.full_name.split(maxsplit=1)
        customer = Customer(
            customer_type=Customer.CustomerType.NATURAL,
            first_name=names[0],
            last_name=names[1] if len(names) > 1 else "",
            email=lead.email,
            phone=lead.phone,
            whatsapp=lead.whatsapp,
            city=lead.city,
            province=lead.province,
            preferred_contact_method=lead.preferred_contact_method or Customer.ContactMethod.WHATSAPP,
            source=f"CRM · {lead.get_source_display()}",
            status=Customer.Status.PROSPECT,
            assigned_branch=lead.branch,
            assigned_advisor=lead.assigned_advisor,
            created_by=actor,
        )
        customer.full_clean()
        customer.save()
    lead.customer = customer
    lead.save(update_fields=["customer", "updated_at"])
    if lead.vehicle_id or lead.interested_brand or lead.interested_model:
        CustomerVehicleInterest.objects.get_or_create(
            customer=customer,
            vehicle=lead.vehicle,
            status=CustomerVehicleInterest.InterestStatus.OPEN,
            defaults={
                "brand": lead.interested_brand,
                "model_name": lead.interested_model,
                "budget_min": lead.budget_min,
                "budget_max": lead.budget_max,
                "notes": lead.message,
                "created_by": actor,
            },
        )
    CustomerNote.objects.create(
        customer=customer,
        note_type=CustomerNote.NoteType.GENERAL,
        title=f"Convertido desde {lead.code}",
        body=lead.message or "Lead convertido desde el CRM.",
        created_by=actor,
    )
    add_system_activity(lead=lead, title="Lead convertido en cliente", activity_type=LeadActivity.ActivityType.CONVERSION, actor=actor, metadata={"customer_id": customer.pk})
    audit_log(user=actor, action="leads.convert_customer", target=lead, after={"customer": customer.pk})
    return customer


@transaction.atomic
def convert_lead_to_customer(*, actor, lead: Lead) -> Customer:
    return _convert_locked_lead_to_customer(actor=actor, lead=_locked_lead(lead))


def _sale_source(lead: Lead) -> str:
    return {
        Lead.Source.WEB_CATALOG: SaleRecord.Source.WEB,
        Lead.Source.WEBSITE: SaleRecord.Source.WEB,
        Lead.Source.SHOWROOM: SaleRecord.Source.SHOWROOM,
        Lead.Source.PHONE: SaleRecord.Source.PHONE,
        Lead.Source.WHATSAPP: SaleRecord.Source.WHATSAPP,
        Lead.Source.REFERRAL: SaleRecord.Source.REFERRAL,
        Lead.Source.FAIR: SaleRecord.Source.FAIR,
    }.get(lead.source, SaleRecord.Source.OTHER)


@transaction.atomic
def create_quote_from_lead(*, actor, lead: Lead) -> SaleRecord:
    lead = _locked_lead(lead)
    if lead.linked_sale_id:
        linked_sale = SaleRecord.objects.get(pk=lead.linked_sale_id)
        if linked_sale.status not in {SaleRecord.Status.CANCELLED, SaleRecord.Status.EXPIRED}:
            return linked_sale
    customer = _convert_locked_lead_to_customer(actor=actor, lead=lead)
    branch = lead.branch or getattr(lead.vehicle, "branch", None) or getattr(actor, "branch", None)
    if branch is None:
        raise ValidationError("Asigna una sucursal antes de generar la cotización.")
    sale = create_sale_from_data(
        actor=actor,
        validated_data={
            "kind": SaleRecord.Kind.QUOTE,
            "customer": customer,
            "branch": branch,
            "advisor": lead.assigned_advisor or actor,
            "vehicle": lead.vehicle,
            "source": _sale_source(lead),
            "vehicle_price": getattr(lead.vehicle, "price", None) or Decimal("0.00"),
            "valid_until": timezone.localdate() + timedelta(days=15),
            "notes": f"Cotización originada desde {lead.code}. {lead.message}".strip(),
        },
        history_note=f"Creada desde lead {lead.code}",
    )
    previous = lead.status
    lead.linked_sale = sale
    lead.customer = customer
    lead.status = Lead.Status.QUOTED
    lead.save(update_fields=["linked_sale", "customer", "status", "updated_at"])
    refresh_lead_score(lead)
    LeadActivity.objects.create(
        lead=lead,
        activity_type=LeadActivity.ActivityType.QUOTE,
        title=f"Cotización {sale.number} creada",
        previous_status=previous,
        new_status=lead.status,
        created_by=actor,
        metadata={"sale_id": sale.pk, "sale_number": sale.number},
    )
    audit_log(user=actor, action="leads.quote.create", target=lead, after={"sale": sale.pk, "number": sale.number})
    return sale
