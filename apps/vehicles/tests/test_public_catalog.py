"""ES: Este módulo especifica regresiones ejecutables para el dominio de vehículos.

EN: This module specifies executable regressions for the vehicles domain.

Contexto existente / Existing context:
Regression coverage for public catalog in the vehicles domain.
"""

import pytest
from django.utils import timezone

from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel


@pytest.mark.django_db
def test_vehicle_catalog_is_public(client):
    response = client.get("/vehicles/")
    assert response.status_code == 200
    assert b"Cat" in response.content


@pytest.mark.django_db
def test_vehicle_catalog_shows_only_available_public_vehicles(client):
    brand = VehicleBrand.objects.create(name="GMC")
    model = VehicleModel.objects.create(brand=brand, name="Canyon")
    Vehicle.objects.create(
        brand=brand,
        model=model,
        year=2023,
        version="AT4X",
        vin="VINPUBLIC123",
        public_slug="gmc-canyon-public",
        status=Vehicle.Status.AVAILABLE,
        published_at=timezone.now(),
    )
    Vehicle.objects.create(
        brand=brand,
        model=model,
        year=2024,
        version="Reservado",
        vin="VINPRIVATE123",
        public_slug="gmc-canyon-private",
        status=Vehicle.Status.RESERVED,
        published_at=timezone.now(),
    )
    Vehicle.objects.create(
        brand=brand,
        model=model,
        year=2025,
        version="Disponible no publicado",
        vin="VINUNPUBLISHED123",
        public_slug="gmc-canyon-unpublished",
        status=Vehicle.Status.AVAILABLE,
    )

    response = client.get("/vehicles/")

    assert response.status_code == 200
    assert b"AT4X" in response.content
    assert b"Reservado" not in response.content
    assert b"Disponible no publicado" not in response.content
