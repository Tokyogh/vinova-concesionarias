"""ES: Este módulo especifica regresiones ejecutables para el dominio de clientes.

EN: This module specifies executable regressions for the customers domain.

Contexto existente / Existing context:
Regression coverage for customer models in the customers domain.
"""

import pytest

from apps.customers.models import Customer


@pytest.mark.django_db
def test_customer_display_name_for_person_and_company():
    person = Customer.objects.create(first_name="Carlos", last_name="Mendoza", identification_number="0912345678")
    company = Customer.objects.create(customer_type=Customer.CustomerType.COMPANY, business_name="Transporte Andino", identification_number="0999999999001")

    assert person.display_name == "Carlos Mendoza"
    assert company.display_name == "Transporte Andino"


@pytest.mark.django_db
def test_customer_primary_contact_priority():
    customer = Customer.objects.create(first_name="Ana", email="ana@example.com", phone="042222333", whatsapp="0999999999")
    assert customer.primary_contact == "0999999999"


@pytest.mark.django_db
def test_customer_normalizes_email_and_phone_contacts():
    customer = Customer.objects.create(
        first_name="Ana",
        email="  ANA@EXAMPLE.COM ",
        phone="+593 (99) 111-2233",
        whatsapp="099 444 55-66",
    )

    assert customer.email == "ana@example.com"
    assert customer.phone == "593991112233"
    assert customer.whatsapp == "0994445566"
