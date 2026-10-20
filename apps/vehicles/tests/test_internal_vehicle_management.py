"""ES: Este módulo especifica regresiones ejecutables para el dominio de vehículos.

EN: This module specifies executable regressions for the vehicles domain.

Contexto existente / Existing context:
Regression coverage for internal vehicle management in the vehicles domain.
"""

import pytest

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel


@pytest.fixture
def vehicle_permissions():
    perms = {}
    for code in ["dashboard.view", "vehicles.view", "vehicles.manage", "vehicles.publish"]:
        perms[code] = PermissionCode.objects.create(module=code.split(".")[0], code=code, name=code)
    return perms


@pytest.fixture
def vehicle_manager(django_user_model, vehicle_permissions):
    user = django_user_model.objects.create_user(username="vehmanager", email="vehmanager@example.com", password="x")
    role = Role.objects.create(code="marketing", name="Marketing / catálogo")
    role.permissions.add(vehicle_permissions["dashboard.view"], vehicle_permissions["vehicles.view"], vehicle_permissions["vehicles.manage"], vehicle_permissions["vehicles.publish"])
    UserRole.objects.create(user=user, role=role)
    return user


@pytest.mark.django_db
def test_internal_vehicle_module_requires_login(client):
    response = client.get("/dashboard/vehicles/")
    assert response.status_code == 302
    assert "/accounts/login/" in response.headers["Location"]


@pytest.mark.django_db
def test_common_user_cannot_access_internal_vehicle_module(client, django_user_model):
    user = django_user_model.objects.create_user(username="clienteveh", email="clienteveh@example.com", password="x")
    client.force_login(user)
    response = client.get("/dashboard/vehicles/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_vehicle_manager_can_create_vehicle(client, vehicle_manager):
    brand = VehicleBrand.objects.create(name="GMC")
    model = VehicleModel.objects.create(brand=brand, name="Canyon", segment="Pickup")
    client.force_login(vehicle_manager)

    response = client.post(
        "/dashboard/vehicles/new/",
        {
            "brand": brand.pk,
            "model": model.pk,
            "year": 2023,
            "version": "AT4X",
            "vin": "VINCREATEV050001",
            "plate": "ABC-1234",
            "color": "Rojo",
            "mileage": 0,
            "price": "65000.00",
            "status": Vehicle.Status.HIDDEN,
            "short_description": "Pickup demo",
            "description": "Ficha interna de prueba",
            "is_featured": "on",
        },
    )

    vehicle = Vehicle.objects.get(vin="VINCREATEV050001")
    assert response.status_code == 302
    assert response.headers["Location"] == f"/dashboard/vehicles/{vehicle.pk}/"
    assert vehicle.public_slug
    assert vehicle.status == Vehicle.Status.HIDDEN


@pytest.mark.django_db
def test_internal_sidebar_does_not_show_public_links(client, vehicle_manager):
    client.force_login(vehicle_manager)
    response = client.get("/dashboard/", follow=True)
    assert response.status_code == 200
    assert b"Inicio p" not in response.content
    assert "Catálogo público".encode() not in response.content
    assert b"Veh" in response.content
