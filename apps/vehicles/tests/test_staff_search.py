"""ES: Este módulo especifica regresiones ejecutables para el dominio de vehículos.

EN: This module specifies executable regressions for the vehicles domain.

Contexto existente / Existing context:
Regression coverage for staff search in the vehicles domain.
"""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel


@pytest.fixture
def vehicle_search_permissions():
    perms = {}
    for code in ["dashboard.view", "vehicles.view", "vehicles.manage", "vehicles.publish"]:
        perms[code] = PermissionCode.objects.create(module=code.split(".")[0], code=code, name=code)
    return perms


@pytest.fixture
def vehicle_search_user(django_user_model, vehicle_search_permissions):
    user = django_user_model.objects.create_user(username="searchveh", email="searchveh@example.com", password="x")
    role = Role.objects.create(code="staff_veh_search", name="Búsqueda vehículos")
    role.permissions.add(*vehicle_search_permissions.values())
    UserRole.objects.create(user=user, role=role)
    return user


@pytest.fixture
def vehicle_branch_scope_user(django_user_model, vehicle_search_permissions):
    company = Company.objects.create(
        legal_name="Empresa Vehículos S.A.", commercial_name="Empresa Vehículos", ruc="1790000000006"
    )
    own = Branch.objects.create(company=company, name="Sucursal V", code="VSRCH-A", branch_type=Branch.BranchType.DEALERSHIP, city="Guayaquil")
    other = Branch.objects.create(company=company, name="Sucursal W", code="VSRCH-B", branch_type=Branch.BranchType.DEALERSHIP, city="Quito")
    user = django_user_model.objects.create_user(username="branchveh", email="branchveh@example.com", password="x")
    role = Role.objects.create(code="branch_veh_search", name="Búsqueda vehículos por sucursal")
    role.permissions.add(*vehicle_search_permissions.values())
    UserRole.objects.create(user=user, role=role, branch=own)
    return user, own, other


def make_vehicle(brand_name="GMC", model_name="Canyon", *, slug, branch=None, **kwargs):
    brand, _ = VehicleBrand.objects.get_or_create(name=brand_name)
    model, _ = VehicleModel.objects.get_or_create(brand=brand, name=model_name, defaults={"segment": "Pickup"})
    defaults = {"brand": brand, "model": model, "year": 2023, "public_slug": slug, "branch": branch}
    defaults.update(kwargs)
    return Vehicle.objects.create(**defaults)


@pytest.mark.django_db
def test_vehicle_search_requires_permission(client, django_user_model, vehicle_search_user):
    assert client.get("/dashboard/vehicles/?vin=VINX").status_code == 302

    normal = django_user_model.objects.create_user(username="sinpermisoveh", email="sinpermisoveh@example.com", password="x")
    client.force_login(normal)
    assert client.get("/dashboard/vehicles/?vin=VINX").status_code == 403

    client.force_login(vehicle_search_user)
    assert client.get("/dashboard/vehicles/?vin=VINX").status_code == 200


@pytest.mark.django_db
def test_search_vehicle_by_vin_plate_and_code(client, vehicle_search_user):
    target = make_vehicle(slug="search-1", vin="VINSEARCH0000001", plate="ABC-1234", internal_code="V-100")
    other = make_vehicle(slug="search-2", vin="VINSEARCH0000002", plate="XYZ-5678", internal_code="V-200")
    client.force_login(vehicle_search_user)

    by_vin = client.get("/dashboard/vehicles/?vin=VINSEARCH0000001")
    assert [v.pk for v in by_vin.context["vehicles"]] == [target.pk]

    by_partial_vin = client.get("/dashboard/vehicles/?vin=VINSEARCH0000002")
    assert [v.pk for v in by_partial_vin.context["vehicles"]] == [other.pk]

    by_plate = client.get("/dashboard/vehicles/?plate=ABC-1234")
    assert [v.pk for v in by_plate.context["vehicles"]] == [target.pk]

    by_code = client.get("/dashboard/vehicles/?internal_code=V-100")
    assert [v.pk for v in by_code.context["vehicles"]] == [target.pk]

    assert other not in by_plate.context["vehicles"]


@pytest.mark.django_db
def test_search_vehicle_by_brand_model_and_status(client, vehicle_search_user):
    target_brand = VehicleBrand.objects.create(name="Chevrolet")
    target_model = VehicleModel.objects.create(brand=target_brand, name="Traverse")
    target_brand_id = target_brand.pk
    target_model_id = target_model.pk
    target = Vehicle.objects.create(
        brand=target_brand, model=target_model, year=2024, plate="CHE-0001", public_slug="chevrolet-traverse",
        status=Vehicle.Status.RESERVED,
    )
    other = make_vehicle(slug="toyota-hilux", brand_name="Toyota", model_name="Hilux", vin="VINTOYOTA0001")
    client.force_login(vehicle_search_user)

    by_brand = client.get(f"/dashboard/vehicles/?brand={target_brand_id}")
    assert {v.pk for v in by_brand.context["vehicles"]} == {target.pk}

    by_model = client.get(f"/dashboard/vehicles/?model={target_model_id}")
    assert {v.pk for v in by_model.context["vehicles"]} == {target.pk}

    by_status = client.get(f"/dashboard/vehicles/?status={Vehicle.Status.RESERVED}")
    assert {v.pk for v in by_status.context["vehicles"]} == {target.pk}

    assert other not in by_model.context["vehicles"]


@pytest.mark.django_db
def test_vehicle_combined_filters(client, vehicle_search_user):
    brand = VehicleBrand.objects.create(name="Ford")
    model = VehicleModel.objects.create(brand=brand, name="Ranger")
    target = Vehicle.objects.create(
        brand=brand, model=model, year=2023, vin="VINFORDCOMBO001", plate="FOR-0001", public_slug="ford-ranger",
        status=Vehicle.Status.AVAILABLE,
    )
    Vehicle.objects.create(
        brand=brand, model=model, year=2023, vin="VINFORDCOMBO002", plate="FOR-0002", public_slug="ford-ranger-2",
        status=Vehicle.Status.SOLD,
    )
    client.force_login(vehicle_search_user)

    response = client.get(f"/dashboard/vehicles/?brand={brand.pk}&status={Vehicle.Status.AVAILABLE}")
    assert [v.pk for v in response.context["vehicles"]] == [target.pk]


@pytest.mark.django_db
def test_short_vehicle_queries_do_not_narrow(client, vehicle_search_user):
    a = make_vehicle(slug="wide-1", brand_name="Nissan", model_name="Frontier")
    b = make_vehicle(slug="wide-2", brand_name="Mazda", model_name="BT-50")
    client.force_login(vehicle_search_user)

    empty = client.get("/dashboard/vehicles/?vin=AB")
    assert {v.pk for v in empty.context["vehicles"]} == {a.pk, b.pk}

    assert len(client.get("/dashboard/vehicles/?plate=X").context["vehicles"]) == 2


@pytest.mark.django_db
def test_vehicle_search_pagination(client, vehicle_search_user):
    for i in range(25):
        make_vehicle(slug=f"pagina-{i:02d}", vin=f"VINPAG{i:02d}000000", plate=f"PG{i:02d}-0001")
    client.force_login(vehicle_search_user)

    page1 = client.get("/dashboard/vehicles/")
    assert len(page1.context["vehicles"]) == 20
    assert page1.context["page_obj"].paginator.count == 25
    assert page1.context["page_obj"].has_next()

    page2 = client.get("/dashboard/vehicles/?page=2")
    assert page2.context["page_obj"].has_previous()
    assert len(page2.context["vehicles"]) == 5


@pytest.mark.django_db
def test_vehicle_branch_scope_applies_to_search(client, vehicle_branch_scope_user):
    user, own, other = vehicle_branch_scope_user
    own_vehicle = make_vehicle(slug="own-veh", branch=own, vin="VINSCOPEOWN01", plate="OWN-0001")
    make_vehicle(slug="other-veh", branch=other, vin="VINSCOPEOTH01", plate="OTH-0001")
    client.force_login(user)

    response = client.get("/dashboard/vehicles/?brand=1")
    assert response.status_code == 200
    assert {v.pk for v in response.context["vehicles"]} == {own_vehicle.pk}

    plate = client.get("/dashboard/vehicles/?plate=OTH-0001")
    assert len(plate.context["vehicles"]) == 0


@pytest.mark.django_db
def test_vehicle_list_avoids_n_plus_one(client, vehicle_search_user):
    from apps.vehicles.selectors import internal_vehicle_queryset

    for i in range(30):
        make_vehicle(slug=f"perf-veh-{i:02d}", vin=f"VINPERF{i:02d}000001", plate=f"PF{i:02d}-1000")
    client.force_login(vehicle_search_user)

    with CaptureQueriesContext(connection) as captured:
        page = list(internal_vehicle_queryset(user=vehicle_search_user)[:20])
    assert len(page) == 20
    assert len(captured.captured_queries) <= 5
