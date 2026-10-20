"""ES: Este módulo especifica regresiones ejecutables para el dominio de CRM y leads.

EN: This module specifies executable regressions for the leads domain.

Contexto existente / Existing context:
Regression coverage for sale lifecycle v110 in the leads domain.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.leads.models import Lead, LeadActivity
from apps.leads.services import create_quote_from_lead
from apps.sales.models import SaleRecord
from apps.sales.services import cancel_sale, confirm_sale, expire_sale, reserve_sale


@pytest.fixture
def lifecycle_context(django_user_model):
    company = Company.objects.create(
        legal_name="Vinova Lifecycle S.A.",
        commercial_name="Vinova Lifecycle",
        ruc="0997776665001",
    )
    branch = Branch.objects.create(
        company=company,
        name="Sucursal Lifecycle",
        code="lifecycle-v110",
        city="Quito",
    )
    actor = django_user_model.objects.create_user(
        username="lifecycle-manager",
        email="lifecycle@example.com",
        password="pass12345",
        branch=branch,
        is_superuser=True,
    )
    customer = Customer.objects.create(
        first_name="Ana",
        last_name="Lifecycle",
        email="ana.lifecycle@example.com",
        phone="0997776655",
        assigned_branch=branch,
        assigned_advisor=actor,
        created_by=actor,
    )
    lead = Lead.objects.create(
        full_name="Ana Lifecycle",
        email=customer.email,
        phone=customer.phone,
        branch=branch,
        assigned_advisor=actor,
        customer=customer,
        status=Lead.Status.QUOTED,
    )
    sale = SaleRecord.objects.create(
        number="COT-LIFECYCLE-1",
        kind=SaleRecord.Kind.QUOTE,
        status=SaleRecord.Status.QUOTED,
        customer=customer,
        branch=branch,
        advisor=actor,
    )
    lead.linked_sale = sale
    lead.save(update_fields=["linked_sale", "updated_at"])
    return {"actor": actor, "branch": branch, "customer": customer, "lead": lead, "sale": sale}


@pytest.mark.django_db
def test_reservation_and_confirmation_advance_origin_lead(lifecycle_context):
    actor = lifecycle_context["actor"]
    sale = lifecycle_context["sale"]
    lead = lifecycle_context["lead"]

    reserve_sale(
        actor=actor,
        sale=sale,
        reserved_until=timezone.now() + timedelta(days=2),
        note="Reserva aceptada",
    )
    lead.refresh_from_db()
    assert lead.status == Lead.Status.NEGOTIATION
    assert lead.closed_at is None

    confirm_sale(actor=actor, sale=sale, note="Venta cerrada")
    lead.refresh_from_db()
    assert lead.status == Lead.Status.WON
    assert lead.closed_at is not None
    assert lead.next_follow_up_at is None
    assert list(
        lead.activities.filter(activity_type=LeadActivity.ActivityType.STATUS)
        .order_by("created_at")
        .values_list("previous_status", "new_status")
    ) == [
        (Lead.Status.QUOTED, Lead.Status.NEGOTIATION),
        (Lead.Status.NEGOTIATION, Lead.Status.WON),
    ]


@pytest.mark.django_db
@pytest.mark.parametrize("transition", [cancel_sale, expire_sale])
def test_terminal_quote_reopens_lead_and_allows_a_new_quote(lifecycle_context, transition):
    actor = lifecycle_context["actor"]
    original_sale = lifecycle_context["sale"]
    lead = lifecycle_context["lead"]

    transition(actor=actor, sale=original_sale, note="Operación sin cierre")
    lead.refresh_from_db()
    assert lead.status == Lead.Status.INTERESTED
    assert lead.linked_sale_id == original_sale.pk

    replacement = create_quote_from_lead(actor=actor, lead=lead)
    lead.refresh_from_db()
    original_sale.refresh_from_db()
    assert replacement.pk != original_sale.pk
    assert replacement.status == SaleRecord.Status.QUOTED
    assert lead.linked_sale_id == replacement.pk
    assert lead.status == Lead.Status.QUOTED
    assert original_sale.status in {SaleRecord.Status.CANCELLED, SaleRecord.Status.EXPIRED}


@pytest.mark.django_db
def test_cancellation_does_not_reopen_a_manually_closed_lead(lifecycle_context):
    sale = lifecycle_context["sale"]
    lead = lifecycle_context["lead"]
    lead.status = Lead.Status.LOST
    lead.lost_reason = "Decisión registrada"
    lead.closed_at = timezone.now()
    lead.save(update_fields=["status", "lost_reason", "closed_at", "updated_at"])

    cancel_sale(actor=lifecycle_context["actor"], sale=sale)

    lead.refresh_from_db()
    assert lead.status == Lead.Status.LOST
    assert lead.lost_reason == "Decisión registrada"
