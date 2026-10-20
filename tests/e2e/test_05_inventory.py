"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for 05 inventory in the e2e domain.
"""

from __future__ import annotations

import re
from decimal import Decimal

import pytest

from apps.inventory.models import InventoryItem
from tests.e2e.helpers.base import VinovaE2EBase
from tests.e2e.helpers.forms import submit_and_wait_for_url, wait_for_database_object

pytestmark = pytest.mark.e2e


class TestInventoryFlow(VinovaE2EBase):
    def test_05_inventory_item_and_stock_flow(self):
        self.login()
        self.page.goto(f"{self.live_server_url}/dashboard/inventory/new/")
        self.page.locator("select[name='category']").select_option(str(self.category.pk))
        self.page.locator("input[name='name']").fill("Aceite E2E")
        self.page.locator("input[name='sku']").fill("OIL-E2E-001")
        self.page.locator("select[name='item_type']").select_option(InventoryItem.ItemType.OIL)
        self.page.locator("input[name='unit']").fill("litro")
        self.page.locator("input[name='price']").fill("12.50")
        self.page.locator("input[name='cost']").fill("7.00")
        self.page.locator("select[name='status']").select_option(InventoryItem.Status.ACTIVE)
        track = self.page.locator("input[name='track_stock']")
        if not track.is_checked():
            track.check()
        submit_and_wait_for_url(
            self.page,
            self.page.get_by_role("button", name="Guardar artículo"),
            re.compile(r".*/dashboard/inventory/\d+/$"),
        )
        created = wait_for_database_object(
            lambda: InventoryItem.objects.get(sku="OIL-E2E-001"),
            description="el artículo de inventario E2E",
        )
        assert f"/dashboard/inventory/{created.pk}/" in self.page.url
        movement_form = self.page.locator("form.inventory-inline-form")
        assert movement_form.count() == 1
        movement_form.locator("select[name='branch']").select_option(str(self.branch.pk))
        movement_form.locator("select[name='movement_type']").select_option("in")
        movement_form.locator("input[name='quantity']").fill("15")
        movement_form.locator("input[name='reference']").fill("E2E-IN")
        submit_and_wait_for_url(
            self.page,
            movement_form.get_by_role("button", name="Guardar movimiento"),
            re.compile(rf".*/dashboard/inventory/{created.pk}/$"),
        )
        created.refresh_from_db()
        assert created.stock_records.get(branch=self.branch).quantity == Decimal("15.00")
