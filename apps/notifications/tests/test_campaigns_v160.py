"""ES: Este módulo especifica regresiones ejecutables para el dominio de notificaciones.

EN: This module specifies executable regressions for the notifications domain.

Contexto existente / Existing context:
Regression coverage for campaigns v160 in the notifications domain.
"""

from __future__ import annotations

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import override_settings
from django.urls import reverse

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer, CustomerVehicleInterest
from apps.notifications.forms import CampaignForm, CampaignMessageForm
from apps.notifications.models import Campaign, CampaignRecipient, NotificationMessage, NotificationRecipient
from apps.notifications.services import calculate_campaign_recipients, confirm_campaign, create_campaign, prepare_campaign_message
from apps.privacy.models import ConsentRecord
from apps.sales.models import SaleRecord
from apps.vehicles.models import VehicleBrand


@pytest.fixture
def campaign_data(django_user_model):
    company = Company.objects.create(legal_name="Campaign SA", commercial_name="Campaign", ruc="1799999999002")
    branch_a = Branch.objects.create(company=company, name="Norte", code="CMP-A", branch_type=Branch.BranchType.DEALERSHIP, city="Quito")
    branch_b = Branch.objects.create(company=company, name="Sur", code="CMP-B", branch_type=Branch.BranchType.DEALERSHIP, city="Quito")
    permissions = [
        PermissionCode.objects.create(module=code.split(".")[0], code=code, name=code)
        for code in ("dashboard.view", "campaigns.view", "campaigns.manage", "campaigns.send", "notifications.view", "notifications.send")
    ]
    role = Role.objects.create(code="campaign_manager", name="Campaign manager")
    role.permissions.add(*permissions)
    manager_a = django_user_model.objects.create_user(username="campaign-a", email="campaign-a@example.com", password="x")
    manager_b = django_user_model.objects.create_user(username="campaign-b", email="campaign-b@example.com", password="x")
    UserRole.objects.create(user=manager_a, role=role, branch=branch_a)
    UserRole.objects.create(user=manager_b, role=role, branch=branch_b)
    customer_a = Customer.objects.create(first_name="Ana", last_name="Norte", email="ana@example.com", identification_number="1100000001", assigned_branch=branch_a)
    customer_b = Customer.objects.create(first_name="Berta", last_name="Sur", email="berta@example.com", identification_number="1100000002", assigned_branch=branch_b)
    ConsentRecord.objects.create(customer=customer_a, purpose=ConsentRecord.Purpose.MARKETING, status=ConsentRecord.Status.GRANTED)
    ConsentRecord.objects.create(customer=customer_b, purpose=ConsentRecord.Purpose.MARKETING, status=ConsentRecord.Status.GRANTED)
    return manager_a, manager_b, branch_a, branch_b, customer_a, customer_b


def _campaign_form(manager, branch, segment_type=Campaign.SegmentType.ALL):
    return CampaignForm(
        data={"name": "Seguimiento", "branch": branch.pk, "consent_purpose": Campaign.ConsentPurpose.MARKETING, "segment_type": segment_type, "inactivity_days": 90},
        user=manager,
    )


@pytest.mark.django_db
def test_campaign_workflow_requires_review_and_explicit_confirmation(campaign_data):
    manager_a, manager_b, branch_a, branch_b, customer_a, customer_b = campaign_data
    form = _campaign_form(manager_a, branch_a)
    assert form.is_valid(), form.errors
    campaign = create_campaign(actor=manager_a, form=form)
    assert campaign.status == Campaign.Status.DRAFT
    assert NotificationMessage.objects.count() == 0

    with pytest.raises(ValidationError):
        confirm_campaign(actor=manager_a, campaign=campaign)

    campaign = calculate_campaign_recipients(actor=manager_a, campaign=campaign)
    assert campaign.status == Campaign.Status.REVIEW
    assert campaign.recipient_count == 1
    assert list(campaign.recipient_snapshots.values_list("customer_id", flat=True)) == [customer_a.pk]
    assert NotificationMessage.objects.count() == 0

    message_form = CampaignMessageForm(
        data={
            "subject": "Hola {customer_name}",
            "body": "Te escribe {branch_name} por {campaign_name}.",
            "channel": Campaign.Channel.IN_APP,
        },
        instance=campaign,
    )
    assert message_form.is_valid(), message_form.errors
    campaign = prepare_campaign_message(actor=manager_a, campaign=campaign, form=message_form)
    assert campaign.status == Campaign.Status.READY
    assert NotificationMessage.objects.count() == 0

    campaign = confirm_campaign(actor=manager_a, campaign=campaign)
    assert campaign.status == Campaign.Status.SENT
    assert campaign.notification_id
    snapshot = CampaignRecipient.objects.get(campaign=campaign)
    assert snapshot.rendered_subject == "Hola Ana Norte"
    assert snapshot.rendered_body == "Te escribe Norte por Seguimiento."
    assert NotificationRecipient.objects.filter(notification=campaign.notification, customer=customer_a).exists()
    assert confirm_campaign(actor=manager_a, campaign=campaign).notification_id == campaign.notification_id
    assert NotificationMessage.objects.count() == 1


@pytest.mark.django_db
def test_campaign_scope_and_safe_variables_are_enforced(campaign_data):
    manager_a, manager_b, branch_a, branch_b, customer_a, customer_b = campaign_data
    form = _campaign_form(manager_a, branch_b)
    assert not form.is_valid()
    foreign_form = _campaign_form(manager_b, branch_b)
    assert foreign_form.is_valid(), foreign_form.errors
    with pytest.raises(PermissionDenied):
        create_campaign(actor=manager_a, form=foreign_form)

    campaign = Campaign.objects.create(name="Sur", branch=branch_b, created_by=manager_b)
    with pytest.raises(PermissionDenied):
        calculate_campaign_recipients(actor=manager_a, campaign=campaign)

    unsafe = CampaignMessageForm(
        data={"subject": "Intento", "body": "{__class__}", "channel": Campaign.Channel.IN_APP},
        instance=campaign,
    )
    assert not unsafe.is_valid()
    assert "Variables no permitidas" in str(unsafe.errors)


@pytest.mark.django_db
@override_settings(VINOVA_MODULE_POST_SALES_ENABLED=False)
def test_service_segment_is_blocked_when_optional_module_is_off(campaign_data):
    manager_a, manager_b, branch_a, branch_b, customer_a, customer_b = campaign_data
    form = _campaign_form(manager_a, branch_a, Campaign.SegmentType.SERVICE)
    assert form.is_valid(), form.errors
    campaign = create_campaign(actor=manager_a, form=form)
    with pytest.raises(ValidationError, match="desactivado"):
        calculate_campaign_recipients(actor=manager_a, campaign=campaign)


@pytest.mark.django_db
def test_campaign_http_flow_does_not_confirm_on_read(client, campaign_data):
    manager_a, manager_b, branch_a, branch_b, customer_a, customer_b = campaign_data
    form = _campaign_form(manager_a, branch_a)
    campaign = create_campaign(actor=manager_a, form=form) if form.is_valid() else None
    campaign = calculate_campaign_recipients(actor=manager_a, campaign=campaign)
    message_form = CampaignMessageForm(
        data={"subject": "Aviso", "body": "Hola {customer_name}", "channel": Campaign.Channel.IN_APP},
        instance=campaign,
    )
    assert message_form.is_valid(), message_form.errors
    campaign = prepare_campaign_message(actor=manager_a, campaign=campaign, form=message_form)
    client.force_login(manager_a)

    response = client.get(reverse("notifications_internal:campaign_detail", kwargs={"pk": campaign.pk}))
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "Campañas" in html
    assert not any(marker in html for marker in ("\u00c3", "\u00c2", "\ufffd"))
    campaign.refresh_from_db()
    assert campaign.status == Campaign.Status.READY
    assert NotificationMessage.objects.count() == 0
    response = client.post(reverse("notifications_internal:campaign_confirm", kwargs={"pk": campaign.pk}))
    assert response.status_code == 302
    campaign.refresh_from_db()
    assert campaign.status == Campaign.Status.SENT


@pytest.mark.django_db
def test_campaign_segments_use_consented_existing_customer_data(campaign_data):
    manager_a, manager_b, branch_a, branch_b, customer_a, customer_b = campaign_data
    no_consent = Customer.objects.create(
        first_name="Sin", last_name="Consentimiento", identification_number="1100000003", assigned_branch=branch_a
    )
    interested = Customer.objects.create(
        first_name="Interesada", identification_number="1100000004", assigned_branch=branch_a
    )
    ConsentRecord.objects.create(
        customer=interested, purpose=ConsentRecord.Purpose.MARKETING, status=ConsentRecord.Status.GRANTED
    )
    brand = VehicleBrand.objects.create(name="Marca Segmento")
    CustomerVehicleInterest.objects.create(customer=interested, brand=brand.name, created_by=manager_a)
    SaleRecord.objects.create(
        number="CMP-SALE-1",
        kind=SaleRecord.Kind.SALE,
        status=SaleRecord.Status.SOLD,
        customer=customer_a,
        branch=branch_a,
        created_by=manager_a,
    )

    brand_campaign = Campaign.objects.create(
        name="Marca", branch=branch_a, segment_type=Campaign.SegmentType.BRAND, brand=brand, created_by=manager_a
    )
    brand_campaign = calculate_campaign_recipients(actor=manager_a, campaign=brand_campaign)
    assert list(brand_campaign.recipient_snapshots.values_list("customer_id", flat=True)) == [interested.pk]

    buyers_campaign = Campaign.objects.create(
        name="Compradores", branch=branch_a, segment_type=Campaign.SegmentType.BUYERS, created_by=manager_a
    )
    buyers_campaign = calculate_campaign_recipients(actor=manager_a, campaign=buyers_campaign)
    assert list(buyers_campaign.recipient_snapshots.values_list("customer_id", flat=True)) == [customer_a.pk]
    assert no_consent.pk not in buyers_campaign.recipient_snapshots.values_list("customer_id", flat=True)


@pytest.mark.django_db
def test_revoked_consent_is_rechecked_at_confirmation(campaign_data):
    manager_a, manager_b, branch_a, branch_b, customer_a, customer_b = campaign_data
    form = _campaign_form(manager_a, branch_a)
    assert form.is_valid(), form.errors
    campaign = calculate_campaign_recipients(actor=manager_a, campaign=create_campaign(actor=manager_a, form=form))
    message_form = CampaignMessageForm(
        data={"subject": "Aviso", "body": "Hola", "channel": Campaign.Channel.IN_APP}, instance=campaign
    )
    assert message_form.is_valid(), message_form.errors
    campaign = prepare_campaign_message(actor=manager_a, campaign=campaign, form=message_form)
    consent = ConsentRecord.objects.get(customer=customer_a, purpose=ConsentRecord.Purpose.MARKETING)
    consent.status = ConsentRecord.Status.REVOKED
    consent.save(update_fields=["status", "updated_at"])

    campaign = confirm_campaign(actor=manager_a, campaign=campaign)
    assert campaign.status == Campaign.Status.CANCELLED
    assert campaign.recipient_count == 0
    assert campaign.recipient_snapshots.count() == 0
    assert NotificationMessage.objects.count() == 0
