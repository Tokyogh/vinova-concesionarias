"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for 06 sales in the e2e domain.
"""

from __future__ import annotations

import re
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.leads.models import Lead
from apps.sales.models import SaleRecord
from tests.e2e.helpers.base import VinovaE2EBase
from tests.e2e.helpers.forms import submit_and_wait_for_url, wait_for_database_object

pytestmark = pytest.mark.e2e


class TestSalesAndInvoicesFlow(VinovaE2EBase):
    def test_06_crm_sales_and_invoice_flow(self):
        self.login()
        self.page.goto(f"{self.live_server_url}/dashboard/leads/new/")
        self.page.locator("select[name='request_type']").select_option(Lead.RequestType.QUOTE)
        self.page.locator("select[name='status']").select_option(Lead.Status.NEW)
        self.page.locator("select[name='priority']").select_option(Lead.Priority.HIGH)
        self.page.locator("select[name='source']").select_option(Lead.Source.SHOWROOM)
        self.page.locator("input[name='full_name']").fill("Prospecto Pruebas")
        self.page.locator("input[name='email']").fill("prospecto.e2e@example.com")
        self.page.locator("select[name='branch']").select_option(str(self.branch.pk))
        submit_and_wait_for_url(
            self.page,
            self.page.get_by_role("button", name="Guardar lead"),
            re.compile(r".*/dashboard/leads/\d+/$"),
        )
        wait_for_database_object(
            lambda: Lead.objects.get(email="prospecto.e2e@example.com"),
            description="el lead E2E",
        )

        self.page.goto(f"{self.live_server_url}/dashboard/sales/new/")
        self.page.locator("select[name='kind']").select_option(SaleRecord.Kind.QUOTE)
        self.page.locator("select[name='customer']").select_option(str(self.customer.pk))
        self.page.locator("select[name='branch']").select_option(str(self.branch.pk))
        self.page.locator("select[name='advisor']").select_option(str(self.admin.pk))
        self.page.locator("select[name='vehicle']").select_option(str(self.vehicle.pk))
        self.page.locator("select[name='source']").select_option(SaleRecord.Source.SHOWROOM)
        self.page.locator("input[name='vehicle_price']").fill("35000")
        self.page.locator("input[name='tax_rate']").fill("15")
        self.page.locator("input[name='valid_until']").fill((timezone.localdate() + timedelta(days=7)).isoformat())
        submit_and_wait_for_url(
            self.page,
            self.page.get_by_role("button").last,
            re.compile(r".*/dashboard/sales/\d+/$"),
        )
        sale = wait_for_database_object(
            lambda: SaleRecord.objects.get(customer=self.customer),
            description="la venta E2E",
        )
        assert sale.status == SaleRecord.Status.QUOTED

        sale.status = SaleRecord.Status.SOLD
        sale.total = Decimal("40250.00")
        sale.balance_due = sale.total
        sale.save(update_fields=["status", "total", "balance_due"])
        self.page.goto(f"{self.live_server_url}/dashboard/invoices/new/?sale={sale.pk}")
        self.page.locator("select[name='sale']").select_option(str(sale.pk))
        self.page.locator("input[name='issue_date']").fill(timezone.localdate().isoformat())
        submit_and_wait_for_url(
            self.page,
            self.page.get_by_role("button", name="Crear borrador"),
            re.compile(r".*/dashboard/invoices/\d+/$"),
        )
        assert sale.invoices.exists()
