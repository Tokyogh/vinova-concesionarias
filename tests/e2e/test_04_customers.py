"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for 04 customers in the e2e domain.
"""

from __future__ import annotations

import re

import pytest

from apps.customers.models import Customer
from tests.e2e.helpers.base import VinovaE2EBase
from tests.e2e.helpers.forms import submit_and_wait_for_url, wait_for_database_object

pytestmark = pytest.mark.e2e


class TestCustomerFlow(VinovaE2EBase):
    def test_04_customer_creation_flow(self):
        self.login()
        self.page.goto(f"{self.live_server_url}/dashboard/customers/new/")
        self.page.locator("select[name='customer_type']").select_option(Customer.CustomerType.NATURAL)
        self.page.locator("input[name='identification_number']").fill("0911453215")
        self.page.locator("input[name='first_name']").fill("María")
        self.page.locator("input[name='last_name']").fill("Pruebas")
        self.page.locator("input[name='email']").fill("maria.e2e@example.com")
        self.page.locator("input[name='phone']").fill("0988888888")
        self.page.locator("select[name='assigned_branch']").select_option(str(self.branch.pk))
        submit_and_wait_for_url(
            self.page,
            self.page.get_by_role("button", name="Guardar cliente"),
            re.compile(r".*/dashboard/customers/\d+/$"),
        )
        created = wait_for_database_object(
            lambda: Customer.objects.get(email="maria.e2e@example.com"),
            description="el cliente E2E",
        )
        assert created.assigned_branch_id == self.branch.pk
        assert f"/dashboard/customers/{created.pk}/" in self.page.url
