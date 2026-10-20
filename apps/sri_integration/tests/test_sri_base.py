"""ES: Este módulo especifica regresiones ejecutables para el dominio de configuración SRI heredada.

EN: This module specifies executable regressions for the sri integration domain.

Contexto existente / Existing context:
Regression coverage for sri base in the sri_integration domain.
"""

import pytest

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.companies.models import Company
from apps.sri_integration.models import SriConfiguration, SriEstablishment, SriSequence
from apps.sri_integration.selectors import get_or_create_sri_configuration


@pytest.fixture
def sri_admin(django_user_model):
    user = django_user_model.objects.create_user(username="sriadmin", email="sriadmin@example.com", password="x")
    perm = PermissionCode.objects.create(module="sri", code="sri.manage", name="Gestionar SRI")
    role = Role.objects.create(code="sri_admin_v014", name="SRI admin v0.14", level=4)
    role.permissions.add(perm)
    UserRole.objects.create(user=user, role=role)
    return user


@pytest.fixture
def company():
    return Company.objects.create(legal_name="Vinova Demo Motors S.A.", commercial_name="Vinova Demo", ruc="1799999999001", is_active=True)


@pytest.mark.django_db
def test_sri_configuration_is_created_from_company(company):
    config = get_or_create_sri_configuration(company)
    assert config.ruc == company.ruc
    assert config.environment == SriConfiguration.Environment.TEST


@pytest.mark.django_db
def test_sri_admin_can_update_configuration(client, sri_admin, company):
    client.force_login(sri_admin)
    response = client.post(
        "/dashboard/company/sri/",
        {
            "ruc": company.ruc,
            "legal_name": company.legal_name,
            "commercial_name": company.commercial_name,
            "matrix_address": "Matriz Quito",
            "environment": SriConfiguration.Environment.TEST,
            "status": SriConfiguration.Status.READY_FOR_TESTS,
            "emission_type": "1",
            "taxpayer_regime": "General",
            "technical_contact_name": "TI",
            "technical_contact_email": "ti@example.com",
            "notes": "Preparado para pruebas",
        },
    )
    assert response.status_code == 302
    config = SriConfiguration.objects.get(company=company)
    assert config.status == SriConfiguration.Status.READY_FOR_TESTS


@pytest.mark.django_db
def test_sri_sequence_preview(company):
    config = get_or_create_sri_configuration(company)
    establishment = SriEstablishment.objects.create(configuration=config, establishment_code="001", emission_point_code="002", name="Sur")
    sequence = SriSequence.objects.create(establishment=establishment, document_type=SriSequence.DocumentType.INVOICE, current_number=9)
    assert sequence.next_number_preview == "001-002-000000010"


@pytest.mark.django_db
def test_invalid_company_ruc_does_not_break_sri_bootstrap():
    company = Company.objects.create(
        legal_name="Empresa técnica",
        commercial_name="Empresa técnica",
        ruc="SMOKE-INVALID-RUC",
        is_active=True,
    )
    config = get_or_create_sri_configuration(company)
    assert config.ruc == ""


@pytest.mark.django_db
def test_sri_form_rejects_non_numeric_or_wrong_length_ruc():
    from apps.sri_integration.forms import SriConfigurationForm

    form = SriConfigurationForm(
        data={
            "ruc": "SMOKE-INVALID",
            "legal_name": "Empresa técnica",
            "commercial_name": "Empresa técnica",
            "matrix_address": "Quito",
            "environment": SriConfiguration.Environment.TEST,
            "status": SriConfiguration.Status.NOT_CONFIGURED,
            "emission_type": "1",
        }
    )
    assert not form.is_valid()
    assert "ruc" in form.errors
