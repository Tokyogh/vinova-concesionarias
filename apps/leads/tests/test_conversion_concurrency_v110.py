"""ES: Este módulo especifica regresiones ejecutables para el dominio de CRM y leads.

EN: This module specifies executable regressions for the leads domain.

Contexto existente / Existing context:
Regression coverage for conversion concurrency v110 in the leads domain.
"""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connections

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer, CustomerNote
from apps.leads.models import Lead, LeadActivity
from apps.leads.services import convert_lead_to_customer, create_quote_from_lead
from apps.sales.models import SaleRecord


@pytest.fixture
def postgresql_only():
    if connections["default"].vendor != "postgresql":
        pytest.skip("La prueba de concurrencia requiere locks reales de PostgreSQL.")


@pytest.fixture
def conversion_context(django_user_model):
    company = Company.objects.create(
        legal_name="Conversión Concurrente S.A.",
        commercial_name="Conversión Concurrente",
        ruc="1790000000022",
    )
    branch = Branch.objects.create(company=company, name="Conversión", code="CONV-01", city="Quito")
    actor = django_user_model.objects.create_user(
        username="conversion-manager",
        email="conversion-manager@example.com",
        password="x",
        branch=branch,
    )
    permissions = [
        PermissionCode.objects.create(module="leads", code="leads.manage", name="Gestionar leads"),
        PermissionCode.objects.create(module="sales", code="sales.quote", name="Crear cotizaciones"),
    ]
    role = Role.objects.create(code="conversion-manager", name="Responsable de conversión")
    role.permissions.set(permissions)
    UserRole.objects.create(user=actor, role=role)
    return actor, branch


def _run_concurrently(*, actor_id, lead_ids, operation):
    barrier = Barrier(len(lead_ids))

    def worker(lead_id):
        connections.close_all()
        try:
            actor = get_user_model().objects.get(pk=actor_id)
            lead = Lead.objects.get(pk=lead_id)
            barrier.wait()
            return operation(actor=actor, lead=lead).pk
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=len(lead_ids)) as pool:
        return list(pool.map(worker, lead_ids))


@pytest.mark.django_db(transaction=True)
def test_same_lead_creates_one_quote_and_one_conversion(conversion_context, postgresql_only):
    actor, branch = conversion_context
    lead = Lead.objects.create(
        full_name="Cliente idempotente",
        email="idempotente@example.com",
        phone="099 500-0001",
        branch=branch,
    )

    sale_ids = _run_concurrently(
        actor_id=actor.pk,
        lead_ids=[lead.pk, lead.pk],
        operation=lambda **kwargs: create_quote_from_lead(**kwargs),
    )

    lead.refresh_from_db()
    assert len(set(sale_ids)) == 1
    assert SaleRecord.objects.filter(pk=lead.linked_sale_id).count() == 1
    assert LeadActivity.objects.filter(lead=lead, activity_type=LeadActivity.ActivityType.CONVERSION).count() == 1
    assert LeadActivity.objects.filter(lead=lead, activity_type=LeadActivity.ActivityType.QUOTE).count() == 1
    assert CustomerNote.objects.filter(customer=lead.customer, title=f"Convertido desde {lead.code}").count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_leads_with_same_identity_reuse_customer(conversion_context, postgresql_only):
    actor, branch = conversion_context
    first = Lead.objects.create(
        full_name="Identidad compartida A",
        email="PERSONA@EXAMPLE.COM",
        whatsapp="099 500-0002",
        branch=branch,
    )
    second = Lead.objects.create(
        full_name="Identidad compartida B",
        email="persona@example.com",
        phone="099-500-0002",
        branch=branch,
    )

    customer_ids = _run_concurrently(
        actor_id=actor.pk,
        lead_ids=[first.pk, second.pk],
        operation=lambda **kwargs: convert_lead_to_customer(**kwargs),
    )

    first.refresh_from_db()
    second.refresh_from_db()
    assert len(set(customer_ids)) == 1
    assert first.customer_id == second.customer_id == customer_ids[0]
    assert Customer.objects.filter(email="persona@example.com", is_deleted=False).count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_quotes_receive_distinct_numbers(conversion_context, postgresql_only):
    actor, branch = conversion_context
    first = Lead.objects.create(full_name="Cotización A", email="quote-a@example.com", branch=branch)
    second = Lead.objects.create(full_name="Cotización B", email="quote-b@example.com", branch=branch)

    sale_ids = _run_concurrently(
        actor_id=actor.pk,
        lead_ids=[first.pk, second.pk],
        operation=lambda **kwargs: create_quote_from_lead(**kwargs),
    )

    numbers = list(SaleRecord.objects.filter(pk__in=sale_ids).values_list("number", flat=True))
    assert len(sale_ids) == 2
    assert len(set(sale_ids)) == 2
    assert len(set(numbers)) == 2


@pytest.mark.django_db(transaction=True)
def test_whatsapp_matches_and_ambiguous_identity_stops_conversion(conversion_context):
    actor, branch = conversion_context
    existing = Customer.objects.create(
        first_name="WhatsApp existente",
        whatsapp="099 500-0003",
        assigned_branch=branch,
    )
    lead = Lead.objects.create(full_name="Contacto WhatsApp", phone="099-500-0003", branch=branch)

    assert convert_lead_to_customer(actor=actor, lead=lead) == existing

    Customer.objects.create(first_name="Duplicado A", phone="0995000004", assigned_branch=branch)
    Customer.objects.create(first_name="Duplicado B", whatsapp="099 500 0004", assigned_branch=branch)
    ambiguous = Lead.objects.create(full_name="Contacto ambiguo", phone="099-500-0004", branch=branch)

    with pytest.raises(ValidationError, match="coincide con varios clientes"):
        convert_lead_to_customer(actor=actor, lead=ambiguous)

    ambiguous.refresh_from_db()
    assert ambiguous.customer_id is None

    other_branch = Branch.objects.create(
        company=branch.company, name="Conversión ajena", code="CONV-02", city="Guayaquil"
    )
    Customer.objects.create(
        first_name="Cliente otra sucursal",
        email="cross-branch@example.com",
        assigned_branch=other_branch,
    )
    cross_branch = Lead.objects.create(
        full_name="Lead sucursal propia", email="cross-branch@example.com", branch=branch
    )
    with pytest.raises(ValidationError, match="pertenece a otra sucursal"):
        convert_lead_to_customer(actor=actor, lead=cross_branch)
