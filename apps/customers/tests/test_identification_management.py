"""ES: Este módulo especifica regresiones ejecutables para el dominio de clientes.

EN: This module specifies executable regressions for the customers domain.

Contexto existente / Existing context:
Regression coverage for identification management in the customers domain.
"""

import pytest
from django.urls import reverse

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.audit.models import AuditLog
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.identification import find_fuzzy_candidates, normalize_identification_data
from apps.customers.models import Customer
from apps.customers.services import update_customer_from_data

VALID_CEDULA_A = "0911453215"
VALID_CEDULA_B = "0911453223"


@pytest.fixture
def manage_permissions():
    perms = {}
    for code in ["dashboard.view", "customers.view", "customers.manage"]:
        perms[code] = PermissionCode.objects.create(module=code.split(".")[0], code=code, name=code)
    return perms


@pytest.fixture
def manager(django_user_model, manage_permissions):
    user = django_user_model.objects.create_user(username="idmanager", email="idmanager@example.com", password="x")
    role = Role.objects.create(code="id_vendedor", name="Vendedor identificación")
    role.permissions.add(*manage_permissions.values())
    UserRole.objects.create(user=user, role=role)
    return user


@pytest.fixture
def branch():
    company = Company.objects.create(legal_name="Identidad S.A.", commercial_name="Identidad", ruc="1790000000006")
    return Branch.objects.create(
        company=company, name="Sucursal ID", code="ID-001", branch_type=Branch.BranchType.DEALERSHIP, city="Quito"
    )


def _form_payload(branch, **overrides):
    payload = {
        "customer_type": "natural",
        "identification_type": "cedula",
        "identification_number": VALID_CEDULA_A,
        "first_name": "Carlos",
        "last_name": "Mendoza",
        "email": "carlos@example.com",
        "phone": "0991111111",
        "whatsapp": "0991111111",
        "preferred_contact_method": "whatsapp",
        "city": "Quito",
        "province": "Pichincha",
        "source": "Web",
        "status": "prospect",
        "assigned_branch": branch.pk,
        "internal_notes": "",
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_form_rejects_invalid_cedula(client, manager, branch):
    client.force_login(manager)
    response = client.post(
        reverse("customers_internal:create"),
        _form_payload(branch, identification_number="0911111111"),
    )
    assert response.status_code == 200
    assert not Customer.objects.filter(identification_number="0911111111").exists()
    assert "identification_number" in response.context["form"].errors


@pytest.mark.django_db
def test_form_normalizes_identification(client, manager, branch):
    client.force_login(manager)
    response = client.post(
        reverse("customers_internal:create"),
        _form_payload(branch, identification_number="09 1145 3215"),
    )
    assert response.status_code == 302
    customer = Customer.objects.get(first_name="Carlos")
    assert customer.identification_number == VALID_CEDULA_A


@pytest.mark.django_db
def test_form_rejects_duplicate_identification(client, manager, branch):
    Customer.objects.create(first_name="Titular", identification_number=VALID_CEDULA_A, assigned_branch=branch)
    client.force_login(manager)
    response = client.post(
        reverse("customers_internal:create"),
        _form_payload(branch, identification_number="09-1145-3215", first_name="Impostor"),
    )
    assert response.status_code == 200
    assert not Customer.objects.filter(first_name="Impostor").exists()
    assert "identification_number" in response.context["form"].errors


@pytest.mark.django_db
def test_form_warns_about_fuzzy_duplicates_without_blocking(client, manager, branch):
    Customer.objects.create(
        first_name="Titular",
        identification_type=Customer.IdentificationType.OTHER,
        identification_number="EC12345678901",
        assigned_branch=branch,
    )
    client.force_login(manager)
    response = client.post(
        reverse("customers_internal:create"),
        _form_payload(
            branch,
            identification_type="other",
            identification_number="EC12345678902",
            first_name="Similar",
        ),
    )
    assert response.status_code == 302
    assert Customer.objects.filter(first_name="Similar").exists()
    followed = client.get(response.headers["Location"])
    rendered_messages = " ".join(str(message) for message in followed.context["messages"])
    assert "identificación similar" in rendered_messages
    assert "Titular" in rendered_messages


@pytest.mark.django_db
def test_fuzzy_candidates_helper_returns_matches():
    Customer.objects.create(first_name="Titular", identification_number="EC12345678901")
    matches = find_fuzzy_candidates("EC12345678902")
    assert len(matches) == 1
    assert matches[0][0].first_name == "Titular"
    assert matches[0][1] >= 0.92


@pytest.mark.django_db
def test_identification_change_is_audited(manager, branch):
    customer = Customer.objects.create(
        first_name="Titular",
        identification_type=Customer.IdentificationType.CEDULA,
        identification_number=VALID_CEDULA_A,
        assigned_branch=branch,
    )
    update_customer_from_data(
        actor=manager,
        customer=customer,
        validated_data={"identification_number": VALID_CEDULA_B},
    )
    customer.refresh_from_db()
    assert customer.identification_number == VALID_CEDULA_B
    log = AuditLog.objects.filter(action="customers.identification_change", object_id=str(customer.pk)).get()
    assert log.before["identification_number"] == VALID_CEDULA_A
    assert log.after["identification_number"] == VALID_CEDULA_B
    assert log.is_sensitive is True


@pytest.mark.django_db
def test_identification_change_audit_absent_when_unchanged(manager, branch):
    customer = Customer.objects.create(first_name="Quieto", identification_number=VALID_CEDULA_A, assigned_branch=branch)
    update_customer_from_data(actor=manager, customer=customer, validated_data={"city": "Cuenca"})
    assert not AuditLog.objects.filter(action="customers.identification_change", object_id=str(customer.pk)).exists()


@pytest.mark.django_db
def test_normalize_identification_data_helper():
    a = Customer.objects.create(first_name="Sucio A", identification_number="placeholder-a")
    c = Customer.objects.create(first_name="Sucio C", identification_number="placeholder-c")
    Customer.objects.filter(pk=a.pk).update(identification_number="17 1101-6091")
    Customer.objects.filter(pk=c.pk).update(identification_number="17.1101.6091")

    stats = normalize_identification_data()

    a.refresh_from_db()
    c.refresh_from_db()
    assert stats["updated"] == 1
    assert stats["skipped"] == 1
    assert a.identification_number == "1711016091"
    assert c.identification_number == "17.1101.6091"
