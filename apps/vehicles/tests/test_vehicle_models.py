"""ES: Este módulo especifica regresiones ejecutables para el dominio de vehículos.

EN: This module specifies executable regressions for the vehicles domain.

Contexto existente / Existing context:
Regression coverage for vehicle models in the vehicles domain.
"""

import pytest
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel
@pytest.mark.django_db
def test_vehicle_string_representation():
    brand=VehicleBrand.objects.create(name='GMC')
    model=VehicleModel.objects.create(brand=brand, name='Canyon')
    vehicle=Vehicle.objects.create(brand=brand, model=model, year=2023, version='AT4X', vin='VINTEST123', public_slug='gmc-canyon-at4x-vintest123')
    assert '2023' in str(vehicle)
    assert 'GMC' in str(vehicle)
