"""ES: Este módulo especifica regresiones ejecutables para el dominio de clientes.

EN: This module specifies executable regressions for the customers domain.

Contexto existente / Existing context:
Regression coverage for internal customer management in the customers domain.
"""

import pytest
from django.utils import timezone

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.audit.models import AuditLog
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer, CustomerNote, CustomerVehicleInterest


@pytest.fixture
def customer_permissions():
    perms = {}
    for code in ["dashboard.view", "customers.view", "customers.manage", "analytics.view"]:
        perms[code] = PermissionCode.objects.create(module=code.split(".")[0], code=code, name=code)
    return perms


@pytest.fixture
def customer_manager(django_user_model, customer_permissions):
    user = django_user_model.objects.create_user(username="custmanager", email="custmanager@example.com", password="x")
    role = Role.objects.create(code="vendedor", name="Vendedor")
    role.permissions.add(customer_permissions["dashboard.view"], customer_permissions["customers.view"], customer_permissions["customers.manage"])
    UserRole.objects.create(user=user, role=role)
    return user


@pytest.fixture
def branch():
    company = Company.objects.create(legal_name="Empresa Demo S.A.", commercial_name="Empresa Demo", ruc="1790000000006")
    return Branch.objects.create(company=company, name="Sucursal Clientes", code="CLI-001", branch_type=Branch.BranchType.DEALERSHIP, city="Guayaquil")


@pytest.fixture
def branch_customer_manager(django_user_model, customer_permissions):
    company = Company.objects.create(
        legal_name="Empresa Alcance S.A.", commercial_name="Empresa Alcance", ruc="1790000000014"
    )
    own_branch = Branch.objects.create(
        company=company,
        name="Sucursal Propia",
        code="CLI-SCOPE-A",
        branch_type=Branch.BranchType.DEALERSHIP,
        city="Guayaquil",
    )
    other_branch = Branch.objects.create(
        company=company,
        name="Sucursal Ajena",
        code="CLI-SCOPE-B",
        branch_type=Branch.BranchType.DEALERSHIP,
        city="Quito",
    )
    user = django_user_model.objects.create_user(
        username="branchcustomer", email="branchcustomer@example.com", password="x"
    )
    role = Role.objects.create(code="branch_customer_manager", name="Gestor de clientes por sucursal")
    role.permissions.add(*customer_permissions.values())
    assignment = UserRole.objects.create(user=user, role=role, branch=own_branch)
    return user, own_branch, other_branch, assignment


@pytest.mark.django_db
def test_internal_customer_module_requires_login(client):
    response = client.get("/dashboard/customers/")
    assert response.status_code == 302
    assert "/accounts/login/" in response.headers["Location"]


@pytest.mark.django_db
def test_common_user_cannot_access_internal_customer_module(client, django_user_model):
    user = django_user_model.objects.create_user(username="clientenormal", email="clientenormal@example.com", password="x")
    client.force_login(user)
    response = client.get("/dashboard/customers/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_customer_manager_can_create_customer(client, customer_manager, branch):
    client.force_login(customer_manager)
    response = client.post(
        "/dashboard/customers/new/",
        {
            "customer_type": Customer.CustomerType.NATURAL,
            "identification_type": Customer.IdentificationType.CEDULA,
            "identification_number": "0911453215",
            "first_name": "Carlos",
            "last_name": "Mendoza",
            "email": "carlos@example.com",
            "phone": "0991111111",
            "whatsapp": "0991111111",
            "preferred_contact_method": Customer.ContactMethod.WHATSAPP,
            "city": "Guayaquil",
            "province": "Guayas",
            "source": "Web",
            "status": Customer.Status.PROSPECT,
            "assigned_branch": branch.pk,
            "assigned_advisor": customer_manager.pk,
            "internal_notes": "Cliente interesado en pickup.",
        },
    )

    customer = Customer.objects.get(identification_number="0911453215")
    assert response.status_code == 302
    assert response.headers["Location"] == f"/dashboard/customers/{customer.pk}/"
    assert customer.created_by == customer_manager


@pytest.mark.django_db
def test_customer_manager_can_add_note_and_interest(client, customer_manager):
    customer = Customer.objects.create(first_name="Ana", last_name="Paredes", identification_number="0922222222")
    client.force_login(customer_manager)

    note_response = client.post(
        f"/dashboard/customers/{customer.pk}/notes/new/",
        {"note_type": CustomerNote.NoteType.CALL, "title": "Llamada", "body": "Solicitó cotización.", "is_important": "on"},
    )
    interest_response = client.post(
        f"/dashboard/customers/{customer.pk}/interests/new/",
        {"brand": "GMC", "model_name": "Canyon", "status": CustomerVehicleInterest.InterestStatus.OPEN, "notes": "Busca versión 4x4."},
    )

    assert note_response.status_code == 302
    assert interest_response.status_code == 302
    assert customer.notes.filter(title="Llamada", is_important=True).exists()
    assert customer.vehicle_interests.filter(brand="GMC", model_name="Canyon").exists()


@pytest.mark.django_db
def test_sidebar_points_to_internal_customers(client, customer_manager):
    client.force_login(customer_manager)
    response = client.get("/dashboard/", follow=True)
    assert response.status_code == 200
    assert b"/dashboard/customers/" in response.content
    assert b"Clientes <span>Pr" not in response.content


@pytest.mark.django_db
def test_branch_scope_isolates_customer_html_and_metrics(client, branch_customer_manager):
    user, own_branch, other_branch, _ = branch_customer_manager
    own = Customer.objects.create(first_name="Cliente propio", assigned_branch=own_branch)
    other = Customer.objects.create(first_name="Cliente ajeno", assigned_branch=other_branch)
    unassigned = Customer.objects.create(first_name="Cliente sin sucursal")
    client.force_login(user)

    response = client.get("/dashboard/customers/")

    assert response.status_code == 200
    assert [customer.pk for customer in response.context["customers"]] == [own.pk]
    assert response.context["metrics"]["total"] == 1
    assert list(response.context["search_form"].fields["branch"].queryset) == [own_branch]
    assert client.get(f"/dashboard/customers/{other.pk}/").status_code == 404
    assert client.get(f"/dashboard/customers/{unassigned.pk}/").status_code == 404
    assert client.get(f"/dashboard/customers/{other.pk}/edit/").status_code == 404
    assert client.post(f"/dashboard/customers/{other.pk}/status/archive/").status_code == 404
    assert client.post(f"/dashboard/customers/{other.pk}/notes/new/", {"body": "No permitido"}).status_code == 404
    assert client.post(f"/dashboard/customers/{other.pk}/interests/new/", {"brand": "No permitido"}).status_code == 404

    create_response = client.get("/dashboard/customers/new/")
    assert list(create_response.context["form"].fields["assigned_branch"].queryset) == [own_branch]
    assert create_response.context["form"].fields["assigned_branch"].required is True


@pytest.mark.django_db
def test_branch_scope_isolates_customer_api_and_relations(client, branch_customer_manager):
    user, own_branch, other_branch, _ = branch_customer_manager
    own = Customer.objects.create(first_name="API propio", assigned_branch=own_branch)
    other = Customer.objects.create(first_name="API ajeno", assigned_branch=other_branch)
    client.force_login(user)

    response = client.get("/api/v1/customers/")

    assert response.status_code == 200
    assert [customer["id"] for customer in response.json()["results"]] == [own.pk]
    assert client.get(f"/api/v1/customers/{other.pk}/").status_code == 404
    assert client.patch(
        f"/api/v1/customers/{other.pk}/", {"first_name": "Intrusión"}, content_type="application/json"
    ).status_code == 404
    assert client.post(
        "/api/v1/customers/",
        {
            "customer_type": Customer.CustomerType.NATURAL,
            "first_name": "Fuera de alcance",
            "assigned_branch": other_branch.pk,
        },
        content_type="application/json",
    ).status_code == 400
    assert client.post(
        "/api/v1/customer-notes/",
        {"customer": other.pk, "note_type": CustomerNote.NoteType.GENERAL, "body": "No permitido"},
        content_type="application/json",
    ).status_code == 400
    assert client.post(
        "/api/v1/customer-interests/",
        {"customer": other.pk, "brand": "No permitido", "status": CustomerVehicleInterest.InterestStatus.OPEN},
        content_type="application/json",
    ).status_code == 400


@pytest.mark.django_db
def test_global_customer_role_retains_global_access(client, customer_manager, branch_customer_manager):
    _, own_branch, other_branch, _ = branch_customer_manager
    own = Customer.objects.create(first_name="Global A", assigned_branch=own_branch)
    other = Customer.objects.create(first_name="Global B", assigned_branch=other_branch)
    unassigned = Customer.objects.create(first_name="Global sin sucursal")
    client.force_login(customer_manager)

    response = client.get("/api/v1/customers/")

    assert response.status_code == 200
    assert {customer["id"] for customer in response.json()["results"]} == {own.pk, other.pk, unassigned.pk}


@pytest.mark.django_db
def test_expired_customer_role_has_no_access(client, branch_customer_manager):
    user, own_branch, _, assignment = branch_customer_manager
    Customer.objects.create(first_name="Cliente propio", assigned_branch=own_branch)
    assignment.expires_at = timezone.now()
    assignment.save(update_fields=["expires_at", "updated_at"])
    client.force_login(user)

    assert client.get("/dashboard/customers/").status_code == 403
    assert client.get("/api/v1/customers/").status_code == 403


@pytest.mark.django_db
def test_customer_executive_profile_uses_analytics_branch_scope(client, branch_customer_manager):
    user, own_branch, other_branch, _ = branch_customer_manager
    own = Customer.objects.create(first_name="Perfil propio", assigned_branch=own_branch)
    other = Customer.objects.create(first_name="Perfil ajeno", assigned_branch=other_branch)
    client.force_login(user)

    assert client.get(f"/dashboard/customers/{own.pk}/profile/").status_code == 200
    assert client.get(f"/dashboard/customers/{other.pk}/profile/").status_code == 404


@pytest.mark.django_db
def test_customer_api_uses_services_soft_delete_and_append_only_children(client, branch_customer_manager):
    user, own_branch, _, _ = branch_customer_manager
    customer = Customer.objects.create(first_name="Cliente API seguro", assigned_branch=own_branch)
    client.force_login(user)

    update = client.patch(
        f"/api/v1/customers/{customer.pk}/",
        {"first_name": "Cliente actualizado", "status": Customer.Status.VIP},
        content_type="application/json",
    )
    assert update.status_code == 200
    customer.refresh_from_db()
    assert customer.first_name == "Cliente actualizado"
    assert customer.status == Customer.Status.PROSPECT
    assert AuditLog.objects.filter(action="customers.update", object_id=str(customer.pk)).exists()

    archive = client.post(f"/api/v1/customers/{customer.pk}/archive/")
    assert archive.status_code == 200
    customer.refresh_from_db()
    assert customer.status == Customer.Status.ARCHIVED
    assert AuditLog.objects.filter(action="customers.archive", object_id=str(customer.pk)).exists()

    note = client.post(
        "/api/v1/customer-notes/",
        {"customer": customer.pk, "note_type": CustomerNote.NoteType.CALL, "title": "Seguimiento", "body": "OK"},
        content_type="application/json",
    )
    assert note.status_code == 201
    note_id = note.json()["id"]
    assert client.patch(
        f"/api/v1/customer-notes/{note_id}/", {"body": "Alterado"}, content_type="application/json"
    ).status_code == 405
    assert client.delete(f"/api/v1/customer-notes/{note_id}/").status_code == 405

    interest = client.post(
        "/api/v1/customer-interests/",
        {"customer": customer.pk, "brand": "GMC", "status": CustomerVehicleInterest.InterestStatus.OPEN},
        content_type="application/json",
    )
    assert interest.status_code == 201
    interest_id = interest.json()["id"]
    assert client.patch(
        f"/api/v1/customer-interests/{interest_id}/",
        {"brand": "Alterado"},
        content_type="application/json",
    ).status_code == 405
    assert client.delete(f"/api/v1/customer-interests/{interest_id}/").status_code == 405

    deleted = client.delete(f"/api/v1/customers/{customer.pk}/")
    assert deleted.status_code == 204
    customer.refresh_from_db()
    assert customer.is_deleted is True
    assert Customer.objects.filter(pk=customer.pk).exists()
    assert AuditLog.objects.filter(action="customers.soft_delete", object_id=str(customer.pk)).exists()
