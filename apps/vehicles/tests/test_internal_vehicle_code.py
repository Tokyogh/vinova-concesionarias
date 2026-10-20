"""ES: Este módulo especifica regresiones ejecutables para el dominio de vehículos.

EN: This module specifies executable regressions for the vehicles domain.

Contexto existente / Existing context:
Regression coverage for internal vehicle code in the vehicles domain.
"""

from django.test import TestCase

from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel


class VehicleInternalCodeTests(TestCase):
    def setUp(self):
        self.brand = VehicleBrand.objects.create(name="Fóton")
        self.model = VehicleModel.objects.create(brand=self.brand, name="Tunland G7")

    def test_internal_code_is_generated_and_vin_is_optional(self):
        first = Vehicle.objects.create(brand=self.brand, model=self.model, year=2026, public_slug="tunland-1")
        second = Vehicle.objects.create(brand=self.brand, model=self.model, year=2026, public_slug="tunland-2")

        self.assertEqual(first.internal_code, "VIN-FOTON-TUNLAND-G7-2026")
        self.assertEqual(second.internal_code, "VIN-FOTON-TUNLAND-G7-2026-02")
        self.assertIsNone(first.vin)
        self.assertIsNone(second.vin)

    def test_real_vin_is_normalized_but_not_generated(self):
        vehicle = Vehicle.objects.create(
            brand=self.brand,
            model=self.model,
            year=2026,
            public_slug="tunland-real-vin",
            vin="  abc123xyz  ",
        )
        self.assertEqual(vehicle.vin, "ABC123XYZ")
        self.assertTrue(vehicle.internal_code.startswith("VIN-FOTON-TUNLAND-G7-2026"))
