"""ES: Regresiones F17 de gestión ampliada y trazabilidad de vehículos.

EN: F17 regressions for expanded vehicle management and traceability.
"""

import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.audit.models import AuditLog
from apps.vehicles.models import (
    Vehicle,
    VehicleBrand,
    VehicleCommercialHighlight,
    VehicleMedia,
    VehicleModel,
    VehiclePartSpecification,
    VehicleResource,
)


def _grant(user, *codes):
    role = Role.objects.create(code=f"vehicle-f17-{user.username}", name="Vehículos F17")
    permissions = [
        PermissionCode.objects.get_or_create(
            module=code.split(".", 1)[0], code=code, defaults={"name": code}
        )[0]
        for code in codes
    ]
    role.permissions.set(permissions)
    UserRole.objects.create(user=user, role=role)


@pytest.fixture
def managed_vehicle(db):
    brand = VehicleBrand.objects.create(name="Marca Gestión")
    model = VehicleModel.objects.create(brand=brand, name="Modelo Gestión")
    return Vehicle.objects.create(
        brand=brand,
        model=model,
        year=2026,
        version="Inicial",
        vin="VINMANAGEMENT00001",
        public_slug="vehiculo-gestion-f17",
        status=Vehicle.Status.HIDDEN,
    )


@pytest.fixture
def vehicle_manager(django_user_model):
    user = django_user_model.objects.create_user(
        username="vehicle-manager-f17", email="vehicle-manager-f17@example.com", password="x"
    )
    _grant(user, "vehicles.view", "vehicles.manage", "vehicles.publish")
    return user


def _vehicle_payload(vehicle, **overrides):
    data = {
        "brand": vehicle.brand_id,
        "model": vehicle.model_id,
        "branch": "",
        "year": vehicle.year,
        "version": vehicle.version,
        "vin": vehicle.vin or "",
        "plate": vehicle.plate,
        "color": vehicle.color,
        "mileage": "" if vehicle.mileage is None else vehicle.mileage,
        "price": "" if vehicle.price is None else vehicle.price,
        "status": vehicle.status,
        "short_description": vehicle.short_description,
        "description": vehicle.description,
        "is_featured": "on" if vehicle.is_featured else "",
        "change_reason": "",
    }
    data.update(overrides)
    return data


@pytest.mark.django_db
def test_sensitive_identity_change_requires_reason_and_is_audited(
    client, vehicle_manager, managed_vehicle
):
    client.force_login(vehicle_manager)
    url = reverse("vehicles_internal:update", kwargs={"pk": managed_vehicle.pk})

    rejected = client.post(url, _vehicle_payload(managed_vehicle, vin="VINMANAGEMENT00002"))
    managed_vehicle.refresh_from_db()
    assert rejected.status_code == 200
    assert managed_vehicle.vin == "VINMANAGEMENT00001"

    accepted = client.post(
        url,
        _vehicle_payload(
            managed_vehicle,
            vin="VINMANAGEMENT00002",
            change_reason="Corrección verificada contra documento del fabricante.",
        ),
    )
    managed_vehicle.refresh_from_db()
    assert accepted.status_code == 302
    assert managed_vehicle.vin == "VINMANAGEMENT00002"
    log = AuditLog.objects.filter(action="vehicles.update", object_id=str(managed_vehicle.pk)).latest("id")
    assert "Corrección verificada" in log.after["change_reason"]


@pytest.mark.django_db
def test_sold_vehicle_identity_cannot_be_rewritten(client, vehicle_manager, managed_vehicle):
    Vehicle.objects.filter(pk=managed_vehicle.pk).update(status=Vehicle.Status.SOLD)
    managed_vehicle.refresh_from_db()
    client.force_login(vehicle_manager)

    response = client.post(
        reverse("vehicles_internal:update", kwargs={"pk": managed_vehicle.pk}),
        _vehicle_payload(
            managed_vehicle,
            year=2025,
            change_reason="Intento controlado de prueba.",
        ),
    )

    managed_vehicle.refresh_from_db()
    assert response.status_code == 200
    assert managed_vehicle.year == 2026


@pytest.mark.django_db
def test_manager_creates_and_updates_highlights_and_specifications(
    client, vehicle_manager, managed_vehicle
):
    client.force_login(vehicle_manager)
    highlight_response = client.post(
        reverse("vehicles_internal:highlight_create", kwargs={"pk": managed_vehicle.pk}),
        {"title": "Autonomía", "value": "450 km", "icon": "energy", "order": 1},
    )
    specification_response = client.post(
        reverse("vehicles_internal:specification_create", kwargs={"pk": managed_vehicle.pk}),
        {
            "part_code": "technology",
            "title": "Conectividad",
            "summary": "Integración móvil",
            "description": "Conexión autorizada por el fabricante.",
            "image": "",
            "specs": json.dumps({"Pantalla": "12 pulgadas"}),
            "hotspot_label": "Consola",
            "hotspot_x": "",
            "hotspot_y": "",
            "hotspot_z": "",
            "order": 2,
        },
    )

    assert highlight_response.status_code == 302
    assert specification_response.status_code == 302
    assert VehicleCommercialHighlight.objects.filter(vehicle=managed_vehicle, title="Autonomía").exists()
    specification = VehiclePartSpecification.objects.get(vehicle=managed_vehicle, title="Conectividad")
    assert specification.specs == {"Pantalla": "12 pulgadas"}
    assert AuditLog.objects.filter(action="vehicles.highlight.create").exists()
    assert AuditLog.objects.filter(action="vehicles.specification.create").exists()


@pytest.mark.django_db
def test_media_metadata_can_be_edited_and_relation_removed_without_deleting_resource(
    client, vehicle_manager, managed_vehicle
):
    resource = VehicleResource.objects.create(
        title="Imagen pruebas",
        resource_type=VehicleResource.ResourceType.IMAGE,
        file=SimpleUploadedFile("vehicle.jpg", b"synthetic-image-content", content_type="image/jpeg"),
    )
    media = VehicleMedia.objects.create(vehicle=managed_vehicle, resource=resource)
    client.force_login(vehicle_manager)

    edited = client.post(
        reverse("vehicles_internal:media_edit", kwargs={"pk": managed_vehicle.pk, "item_pk": media.pk}),
        {"media_type": "hero", "title": "Vista principal", "alt_text": "Vista frontal", "order": 1, "is_public": "on"},
    )
    media.refresh_from_db()
    assert edited.status_code == 302
    assert media.media_type == VehicleMedia.MediaType.HERO
    assert media.alt_text == "Vista frontal"

    removed = client.post(
        reverse("vehicles_internal:media_delete", kwargs={"pk": managed_vehicle.pk, "item_pk": media.pk})
    )
    assert removed.status_code == 302
    assert not VehicleMedia.objects.filter(pk=media.pk).exists()
    assert VehicleResource.objects.filter(pk=resource.pk).exists()


@pytest.mark.django_db
def test_view_only_user_cannot_reach_vehicle_management_routes(
    client, django_user_model, managed_vehicle
):
    viewer = django_user_model.objects.create_user(username="vehicle-viewer-f17", password="x")
    _grant(viewer, "vehicles.view")
    client.force_login(viewer)

    response = client.get(reverse("vehicles_internal:highlight_create", kwargs={"pk": managed_vehicle.pk}))

    assert response.status_code == 403
