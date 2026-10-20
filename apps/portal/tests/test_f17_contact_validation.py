"""ES: Regresiones F17 para contacto, obligatoriedad contextual y persistencia.

EN: F17 regressions for contact data, contextual requirements, and persistence.
"""

from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command

from apps.customers.models import Customer
from apps.leads.forms import MAX_COMMERCIAL_BUDGET, PublicLeadForm
from apps.portal.forms import PortalCustomerProfileForm
from apps.privacy.forms import PublicDataSubjectRequestForm


def _profile_data(**overrides):
    data = {
        "phone": "099 123 4567",
        "whatsapp": "+593 99 123 4567",
        "address": "Av. República N34-120",
        "city": "Quito",
        "province": "Pichincha",
        "preferred_contact_method": "phone",
    }
    data.update(overrides)
    return data


def _lead_data(**overrides):
    data = {
        "request_type": "quote",
        "full_name": "Persona Pruebas",
        "email": "pruebas@example.com",
        "phone": "",
        "whatsapp": "",
        "preferred_contact_method": "email",
        "city": "Quito",
        "province": "Pichincha",
        "budget_min": "15000.25",
        "budget_max": "30000.50",
        "expected_purchase_date": "",
        "message": "Consulta comercial controlada.",
        "consent_data_processing": "on",
        "website": "",
    }
    data.update(overrides)
    return data


def test_portal_profile_rejects_alphabetic_phone_and_whatsapp():
    form = PortalCustomerProfileForm(data=_profile_data(phone="abc", whatsapp="texto"))

    assert not form.is_valid()
    assert "phone" in form.errors
    assert "whatsapp" in form.errors


def test_portal_profile_accepts_local_and_international_phone_formats():
    form = PortalCustomerProfileForm(data=_profile_data())

    assert form.is_valid(), form.errors


def test_portal_profile_requires_only_selected_contact_channel():
    phone_form = PortalCustomerProfileForm(data=_profile_data(phone="", preferred_contact_method="phone"))
    in_person_form = PortalCustomerProfileForm(
        data=_profile_data(phone="", whatsapp="", preferred_contact_method="in_person")
    )

    assert not phone_form.is_valid()
    assert "phone" in phone_form.errors
    assert in_person_form.is_valid(), in_person_form.errors


def test_privacy_request_rejects_invalid_phone_without_persisting(db):
    form = PublicDataSubjectRequestForm(
        data={
            "request_type": "access",
            "requester_name": "Persona Pruebas",
            "requester_email": "",
            "requester_phone": "llámame",
            "identification_hint": "",
            "description": "Solicitud controlada.",
            "privacy_acknowledgement": "on",
            "website": "",
        }
    )

    assert not form.is_valid()
    assert "requester_phone" in form.errors


@pytest.mark.parametrize("value", ["5 usd", "12.345", str(MAX_COMMERCIAL_BUDGET + Decimal("0.01"))])
def test_public_commercial_request_rejects_malformed_or_out_of_range_budget(value):
    form = PublicLeadForm(data=_lead_data(budget_min=value))

    assert not form.is_valid()
    assert "budget_min" in form.errors


def test_public_commercial_request_accepts_decimal_budget_and_stays_public():
    form = PublicLeadForm(data=_lead_data())

    assert form.is_valid(), form.errors
    assert form.cleaned_data["budget_min"] == Decimal("15000.25")


def test_public_request_requires_the_selected_contact_channel():
    form = PublicLeadForm(data=_lead_data(email="", phone="0991234567", preferred_contact_method="email"))

    assert not form.is_valid()
    assert "email" in form.errors


@pytest.mark.django_db
def test_contact_audit_reports_legacy_record_without_exposing_value():
    customer = Customer.objects.create(first_name="Registro")
    Customer.objects.filter(pk=customer.pk).update(phone="texto heredado")
    output = StringIO()

    call_command("audit_contact_data", stdout=output)

    report = output.getvalue()
    assert f"customers.Customer pk={customer.pk} campo=phone" in report
    assert "texto heredado" not in report
    customer.refresh_from_db()
    assert customer.phone == "texto heredado"
