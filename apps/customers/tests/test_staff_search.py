"""ES: Este módulo especifica regresiones ejecutables para el dominio de clientes.

EN: This module specifies executable regressions for the customers domain.

Contexto existente / Existing context:
Regression coverage for staff search in the customers domain.
"""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer, CustomerVehicleInterest
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel


@pytest.fixture
def branch():
    company = Company.objects.create(legal_name="Empresa Demo S.A.", commercial_name="Empresa Demo", ruc="1790000000006")
    return Branch.objects.create(company=company, name="Sucursal Búsqueda", code="SRCH-001", branch_type=Branch.BranchType.DEALERSHIP, city="Guayaquil")


@pytest.fixture
def search_permissions():
    perms = {}
    for code in ["dashboard.view", "customers.view", "customers.manage"]:
        perms[code] = PermissionCode.objects.create(module=code.split(".")[0], code=code, name=code)
    return perms


@pytest.fixture
def search_user(django_user_model, search_permissions):
    user = django_user_model.objects.create_user(username="searchstaff", email="searchstaff@example.com", password="x")
    role = Role.objects.create(code="staff_search", name="Búsqueda staff")
    role.permissions.add(*search_permissions.values())
    UserRole.objects.create(user=user, role=role)
    return user


@pytest.fixture
def branch_scope_user(django_user_model, search_permissions):
    company = Company.objects.create(
        legal_name="Empresa Búsqueda S.A.", commercial_name="Empresa Búsqueda", ruc="1790000000006"
    )
    own_branch = Branch.objects.create(
        company=company, name="Sucursal B", code="SRCH-A", branch_type=Branch.BranchType.DEALERSHIP, city="Guayaquil"
    )
    other_branch = Branch.objects.create(
        company=company, name="Sucursal C", code="SRCH-B", branch_type=Branch.BranchType.DEALERSHIP, city="Quito"
    )
    user = django_user_model.objects.create_user(username="branchsearch", email="branchsearch@example.com", password="x")
    role = Role.objects.create(code="branch_search", name="Búsqueda por sucursal")
    role.permissions.add(*search_permissions.values())
    UserRole.objects.create(user=user, role=role, branch=own_branch)
    return user, own_branch, other_branch


def make_vehicle(brand_name="GMC", model_name="Canyon", **kwargs):
    brand = VehicleBrand.objects.create(name=brand_name)
    model = VehicleModel.objects.create(brand=brand, name=model_name, segment="Pickup")
    defaults = {
        "brand": brand,
        "model": model,
        "year": 2023,
        "public_slug": f"slug-{kwargs.pop('slug', brand_name.lower() + model_name.lower())}",
    }
    defaults.update(kwargs)
    return Vehicle.objects.create(**defaults)


@pytest.mark.django_db
def test_search_requires_permission(client, django_user_model, search_user):
    response = client.get("/dashboard/customers/?q=buscador")
    assert response.status_code == 302

    normal = django_user_model.objects.create_user(username="sinpermiso", email="sinpermiso@example.com", password="x")
    client.force_login(normal)
    assert client.get("/dashboard/customers/?q=buscador").status_code == 403

    client.force_login(search_user)
    response = client.get("/dashboard/customers/?q=buscador")
    assert response.status_code == 200


@pytest.mark.django_db
def test_search_by_cedula_exact_and_ruc_exact(client, search_user, branch):
    a = Customer.objects.create(first_name="Ana", last_name="Torres", identification_number="0911453215", assigned_branch=branch)
    b = Customer.objects.create(first_name="Bruno", last_name="Reyes", identification_number="1701234567", assigned_branch=branch)
    c = Customer.objects.create(business_name="Importadora Sur", identification_number="0999999999001", assigned_branch=branch, customer_type=Customer.CustomerType.COMPANY)
    client.force_login(search_user)

    response = client.get("/dashboard/customers/?identification=0911453215")
    assert response.status_code == 200
    assert [c.pk for c in response.context["customers"]] == [a.pk]

    response = client.get("/dashboard/customers/?identification=0999999999001")
    assert [c.pk for c in response.context["customers"]] == [c.pk]

    assert b not in response.context["customers"]


@pytest.mark.django_db
def test_search_by_identification_partial_match(client, search_user, branch):
    Customer.objects.create(first_name="Ana", last_name="Torres", identification_number="0911453215", assigned_branch=branch)
    Customer.objects.create(first_name="Bruno", last_name="Reyes", identification_number="1701234567", assigned_branch=branch)
    client.force_login(search_user)

    response = client.get("/dashboard/customers/?identification=09114532")
    assert response.status_code == 200
    assert len(response.context["customers"]) == 1
    assert response.context["customers"][0].identification_number == "0911453215"


@pytest.mark.django_db
def test_search_by_name_email_phone(client, search_user, branch):
    target = Customer.objects.create(
        first_name="Carla", last_name="Figueroa", email="carla.f@example.com", phone="0991234567", assigned_branch=branch
    )
    Customer.objects.create(first_name="Diego", last_name="Naranjo", email="diego@example.com", phone="0997654321", assigned_branch=branch)
    client.force_login(search_user)

    first = client.get("/dashboard/customers/?first_name=Carla")
    assert [c.pk for c in first.context["customers"]] == [target.pk]

    last = client.get("/dashboard/customers/?last_name=Figueroa")
    assert [c.pk for c in last.context["customers"]] == [target.pk]

    email = client.get("/dashboard/customers/?email=carla.f@")
    assert [c.pk for c in email.context["customers"]] == [target.pk]

    phone = client.get("/dashboard/customers/?phone=0991234567")
    assert [c.pk for c in phone.context["customers"]] == [target.pk]


@pytest.mark.django_db
def test_search_customer_by_plate_and_vin(client, search_user, branch):
    owner = Customer.objects.create(first_name="Elena", last_name="Molina", assigned_branch=branch)
    other = Customer.objects.create(first_name="Felipe", last_name="Castro", assigned_branch=branch)
    vehicle = make_vehicle(slug="gmc-canyon-plate", vin="VINPLATESRCH01", plate="ABC-1234")
    CustomerVehicleInterest.objects.create(customer=owner, vehicle=vehicle, status=CustomerVehicleInterest.InterestStatus.OPEN)
    client.force_login(search_user)

    plate = client.get("/dashboard/customers/?plate=ABC-1234")
    assert [c.pk for c in plate.context["customers"]] == [owner.pk]

    vin = client.get("/dashboard/customers/?vin=VINPLATESRCH01")
    assert [c.pk for c in vin.context["customers"]] == [owner.pk]

    assert other not in vin.context["customers"]
    assert other not in plate.context["customers"]


@pytest.mark.django_db
def test_search_combined_filters(client, search_user, branch):
    target = Customer.objects.create(
        first_name="Gina", last_name="Palacios", email="gina@example.com", customer_type=Customer.CustomerType.NATURAL,
        status=Customer.Status.ACTIVE, assigned_branch=branch,
    )
    Customer.objects.create(
        first_name="Gina", last_name="Rivera", email="gina.r@example.com", customer_type=Customer.CustomerType.NATURAL,
        status=Customer.Status.PROSPECT, assigned_branch=branch,
    )
    client.force_login(search_user)

    response = client.get("/dashboard/customers/?last_name=Palacios&status=active&customer_type=natural")
    assert [c.pk for c in response.context["customers"]] == [target.pk]


@pytest.mark.django_db
def test_short_or_empty_query_does_not_narrow_results(client, search_user, branch):
    a = Customer.objects.create(first_name="Hilda", assigned_branch=branch)
    b = Customer.objects.create(first_name="Ivan", assigned_branch=branch)
    client.force_login(search_user)

    one_char = client.get("/dashboard/customers/?q=h")
    assert response_pks(one_char) == {a.pk, b.pk}

    empty = client.get("/dashboard/customers/?q=")
    assert response_pks(empty) == {a.pk, b.pk}

    too_short_field = client.get("/dashboard/customers/?first_name=x")
    assert response_pks(too_short_field) == {a.pk, b.pk}


def response_pks(response):
    return {customer.pk for customer in response.context["customers"]}


@pytest.mark.django_db
def test_search_pagination(client, search_user, branch):
    for i in range(25):
        Customer.objects.create(first_name=f"Pagina{i:02d}", assigned_branch=branch)
    client.force_login(search_user)

    page1 = client.get("/dashboard/customers/")
    assert page1.status_code == 200
    assert len(page1.context["customers"]) == 20
    assert page1.context["page_obj"].paginator.count == 25
    assert page1.context["page_obj"].has_next()

    page2 = client.get("/dashboard/customers/?page=2")
    assert page2.context["page_obj"].has_previous()
    assert len(page2.context["customers"]) == 5


@pytest.mark.django_db
def test_branch_scope_applies_to_search_params(client, branch_scope_user):
    user, own_branch, other_branch = branch_scope_user
    own = Customer.objects.create(first_name="Zoe", last_name="Zambrano", assigned_branch=own_branch)
    Customer.objects.create(first_name="Zoe", last_name="Arias", assigned_branch=other_branch)
    client.force_login(user)

    response = client.get("/dashboard/customers/?last_name=za")
    assert response.status_code == 200
    assert response_pks(response) == {own.pk}

    response = client.get("/dashboard/customers/?identification=0911453215")
    assert response.status_code == 200
    assert response_pks(response) == set()


@pytest.mark.django_db
def test_list_avoids_n_plus_one(client, search_user, branch):
    from apps.customers.selectors import customer_list_queryset

    for i in range(30):
        Customer.objects.create(first_name=f"Perf{i:02d}", last_name="Queries", assigned_branch=branch)
    client.force_login(search_user)

    with CaptureQueriesContext(connection) as captured:
        page = list(customer_list_queryset(user=search_user)[:20])
    assert len(page) == 20
    assert len(captured.captured_queries) <= 3
