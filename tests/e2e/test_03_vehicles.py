"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for 03 vehicles in the e2e domain.
"""

from __future__ import annotations

import re

import pytest

from apps.vehicles.models import Vehicle
from tests.e2e.helpers.base import VinovaE2EBase
from tests.e2e.helpers.forms import submit_and_wait_for_url, wait_for_database_object

pytestmark = pytest.mark.e2e


class TestVehicleFlow(VinovaE2EBase):
    def test_03_vehicle_creation_flow(self):
        self.login()
        self.page.goto(f"{self.live_server_url}/dashboard/vehicles/new/")
        self.page.locator("select[name='brand']").select_option(str(self.brand.pk))
        self.page.locator("select[name='model']").select_option(str(self.vehicle_model.pk))
        self.page.locator("select[name='branch']").select_option(str(self.branch.pk))
        self.page.locator("input[name='year']").fill("2025")
        self.page.locator("input[name='version']").fill("E2E Edition")
        self.page.locator("input[name='vin']").fill("VINQA000000000002")
        self.page.locator("input[name='price']").fill("42000")
        self.page.locator("select[name='status']").select_option(Vehicle.Status.AVAILABLE)
        submit_and_wait_for_url(
            self.page,
            self.page.get_by_role("button", name="Guardar vehículo"),
            re.compile(r".*/dashboard/vehicles/\d+/$"),
        )
        created = wait_for_database_object(
            lambda: Vehicle.objects.get(vin="VINQA000000000002"),
            description="el vehículo E2E",
        )
        assert f"/dashboard/vehicles/{created.pk}/" in self.page.url
