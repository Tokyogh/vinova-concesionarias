"""ES: Este módulo especifica regresiones ejecutables para el dominio de vehículos.

EN: This module specifies executable regressions for the vehicles domain.

Contexto existente / Existing context:
Regression coverage for vehicle scope integrity v120 in the vehicles domain.
"""

from decimal import Decimal

import pytest

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.audit.models import AuditLog
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel


def vehicle_scope_context(django_user_model):
    company = Company.objects.create(
        legal_name="Vehículos Integridad S.A.",
        commercial_name="Vehículos Integridad",
        ruc="1799999999019",
    )
    own_branch = Branch.objects.create(
        company=company,
        name="Vehículos Norte",
        code="VEH-NORTE",
        city="Quito",
    )
    other_branch = Branch.objects.create(
        company=company,
        name="Vehículos Sur",
        code="VEH-SUR",
        city="Cuenca",
    )
    permissions = {
        code: PermissionCode.objects.create(module="vehicles", code=code, name=code)
        for code in ("vehicles.view", "vehicles.manage", "vehicles.publish")
    }
    role = Role.objects.create(code="vehículos_norte", name="Vehículos norte")
    role.permissions.add(*permissions.values())
    user = django_user_model.objects.create_user(
        username="vehículos-norte",
        email="vehiculos-norte@example.com",
        password="x",
    )
    UserRole.objects.create(user=user, role=role, branch=own_branch)
    brand = VehicleBrand.objects.create(name="Scope Motors")
    model = VehicleModel.objects.create(brand=brand, name="Scope One")
    own_vehicle = Vehicle.objects.create(
        brand=brand,
        model=model,
        branch=own_branch,
        year=2026,
        version="Visible propia",
        vin="VEHSCOPEOWN00001",
        price=Decimal("25000.00"),
        status=Vehicle.Status.HIDDEN,
        public_slug="veh-scope-own",
    )
    other_vehicle = Vehicle.objects.create(
        brand=brand,
        model=model,
        branch=other_branch,
        year=2026,
        version="Fuera de alcance",
        vin="VEHSCOPEOTHER001",
        price=Decimal("26000.00"),
        status=Vehicle.Status.HIDDEN,
        public_slug="veh-scope-other",
    )
    unassigned_vehicle = Vehicle.objects.create(
        brand=brand,
        model=model,
        year=2026,
        version="Sin sucursal global",
        vin="VEHSCOPEGLOBAL01",
        price=Decimal("27000.00"),
        status=Vehicle.Status.HIDDEN,
        public_slug="veh-scope-global",
    )
    return user, own_branch, other_branch, brand, model, own_vehicle, other_vehicle, unassigned_vehicle


@pytest.mark.django_db
def test_vehicle_html_and_api_are_scoped_to_active_role_branch(client, django_user_model):
    user, own_branch, other_branch, _, _, own, other, unassigned = vehicle_scope_context(django_user_model)
    client.force_login(user)

    html = client.get("/dashboard/vehicles/")
    assert html.status_code == 200
    assert own.version.encode() in html.content
    assert other.version.encode() not in html.content
    assert unassigned.version.encode() not in html.content
    assert own_branch.name.encode() in html.content
    assert other_branch.name.encode() not in html.content

    api = client.get("/api/v1/vehicles/")
    assert api.status_code == 200
    payload = str(api.data)
    assert own.version in payload
    assert other.version not in payload
    assert unassigned.version not in payload
    assert client.get(f"/api/v1/vehicles/{other.pk}/").status_code == 404
    assert client.get(f"/dashboard/vehicles/{other.pk}/").status_code == 404


@pytest.mark.django_db
def test_vehicle_api_reuses_services_and_rejects_cross_branch_mutations(client, django_user_model):
    user, own_branch, other_branch, brand, model, own, other, _ = vehicle_scope_context(django_user_model)
    client.force_login(user)

    create_other = client.post(
        "/api/v1/vehicles/",
        {
            "brand": brand.pk,
            "model": model.pk,
            "branch": other_branch.pk,
            "year": 2026,
            "version": "Creación cruzada",
            "vin": "VEHCROSSCREATE1",
            "price": "20000.00",
            "status": Vehicle.Status.HIDDEN,
        },
        content_type="application/json",
    )
    assert create_other.status_code == 400
    assert not Vehicle.objects.filter(vin="VEHCROSSCREATE1").exists()

    create_unassigned = client.post(
        "/api/v1/vehicles/",
        {
            "brand": brand.pk,
            "model": model.pk,
            "branch": None,
            "year": 2026,
            "version": "Creación sin sucursal",
            "vin": "VEHUNASSIGNED01",
            "price": "20000.00",
            "status": Vehicle.Status.HIDDEN,
        },
        content_type="application/json",
    )
    assert create_unassigned.status_code == 400
    assert not Vehicle.objects.filter(vin="VEHUNASSIGNED01").exists()

    move = client.patch(
        f"/api/v1/vehicles/{own.pk}/",
        {"branch": other_branch.pk},
        content_type="application/json",
    )
    assert move.status_code == 400
    own.refresh_from_db()
    assert own.branch_id == own_branch.pk

    assert client.patch(
        f"/api/v1/vehicles/{other.pk}/",
        {"color": "Negro"},
        content_type="application/json",
    ).status_code == 404
    assert client.delete(f"/api/v1/vehicles/{own.pk}/").status_code == 405

    created = client.post(
        "/api/v1/vehicles/",
        {
            "brand": brand.pk,
            "model": model.pk,
            "branch": own_branch.pk,
            "year": 2026,
            "version": "Creación segura",
            "vin": "VEHSAFECREATE01",
            "price": "21000.00",
            "status": Vehicle.Status.HIDDEN,
        },
        content_type="application/json",
    )
    assert created.status_code == 201
    vehicle = Vehicle.objects.get(vin="VEHSAFECREATE01")
    assert vehicle.internal_code
    assert vehicle.public_slug
    assert AuditLog.objects.filter(
        action="vehicles.create",
        object_id=str(vehicle.pk),
        branch=own_branch,
    ).exists()


@pytest.mark.django_db
def test_catalog_actions_cannot_overwrite_commercial_vehicle_states(client, django_user_model):
    user, _, _, _, _, own, _, _ = vehicle_scope_context(django_user_model)
    own.status = Vehicle.Status.RESERVED
    own.save(update_fields=["status", "updated_at"])
    client.force_login(user)

    response = client.post(f"/dashboard/vehicles/{own.pk}/publish/")

    assert response.status_code == 302
    own.refresh_from_db()
    assert own.status == Vehicle.Status.RESERVED
    assert not AuditLog.objects.filter(action="vehicles.publish", object_id=str(own.pk)).exists()

    api_response = client.patch(
        f"/api/v1/vehicles/{own.pk}/",
        {"status": Vehicle.Status.AVAILABLE},
        content_type="application/json",
    )
    assert api_response.status_code == 400
    own.refresh_from_db()
    assert own.status == Vehicle.Status.RESERVED


@pytest.mark.django_db
def test_manage_permission_cannot_publish_without_branch_publish_permission(client, django_user_model):
    user, _, _, _, _, own, _, _ = vehicle_scope_context(django_user_model)
    publish_permission = PermissionCode.objects.get(code="vehicles.publish")
    user.user_roles.get().role.permissions.remove(publish_permission)
    client.force_login(user)

    api_response = client.patch(
        f"/api/v1/vehicles/{own.pk}/",
        {"status": Vehicle.Status.AVAILABLE},
        content_type="application/json",
    )
    html_response = client.post(f"/dashboard/vehicles/{own.pk}/publish/")

    assert api_response.status_code == 400
    assert html_response.status_code == 403
    own.refresh_from_db()
    assert own.status == Vehicle.Status.HIDDEN
    assert not AuditLog.objects.filter(action="vehicles.publish", object_id=str(own.pk)).exists()


@pytest.mark.django_db
def test_vehicle_admin_cannot_bypass_scoped_services(client, django_user_model):
    user, _, _, _, _, own, _, _ = vehicle_scope_context(django_user_model)
    user.is_staff = True
    user.is_superuser = True
    user.save(update_fields=["is_staff", "is_superuser"])
    client.force_login(user)

    assert client.get("/admin/vehicles/vehicle/add/").status_code == 403
    response = client.get(f"/admin/vehicles/vehicle/{own.pk}/change/")
    assert response.status_code == 200
    assert b'name="status"' not in response.content
    assert b'name="branch"' not in response.content
