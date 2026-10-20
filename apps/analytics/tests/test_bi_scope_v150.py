"""ES: Este módulo especifica regresiones ejecutables para el dominio de analítica.

EN: This module specifies executable regressions for the analytics domain.

Contexto existente / Existing context:
Regression coverage for bi scope v150 in the analytics domain.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.analytics.selectors import commercial_dashboard_data
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.inventory.models import BranchStock, InventoryItem
from apps.leads.models import Lead
from apps.sales.models import SalePayment, SaleRecord


class BusinessIntelligenceScopeTests(TestCase):
    def setUp(self):
        company = Company.objects.create(legal_name="BI Scope S.A.", commercial_name="BI Scope", ruc="0999999996001")
        self.branch_a = Branch.objects.create(company=company, name="BI A", code="bi-a", city="Quito")
        self.branch_b = Branch.objects.create(company=company, name="BI B", code="bi-b", city="Cuenca")
        view = PermissionCode.objects.create(module="analytics", code="analytics.view", name="Ver BI")
        export = PermissionCode.objects.create(module="analytics", code="analytics.export", name="Exportar BI")
        role = Role.objects.create(code="bi_branch_test", name="BI sucursal")
        role.permissions.add(view, export)
        User = get_user_model()
        self.user = User.objects.create_user(username="bi-a", email="bi-a@example.com", password="x")
        UserRole.objects.create(user=self.user, role=role, branch=self.branch_a)
        customer_a = Customer.objects.create(first_name="Cliente", last_name="A", email="bi-customer-a@example.com", assigned_branch=self.branch_a, assigned_advisor=self.user)
        customer_b = Customer.objects.create(first_name="Cliente", last_name="B", email="bi-customer-b@example.com", assigned_branch=self.branch_b)
        self.sale_a = SaleRecord.objects.create(number="BI-SALE-A", kind=SaleRecord.Kind.SALE, status=SaleRecord.Status.SOLD, customer=customer_a, branch=self.branch_a, advisor=self.user, total=Decimal("100.00"), amount_paid=Decimal("40.00"), balance_due=Decimal("60.00"))
        sale_b = SaleRecord.objects.create(number="BI-SALE-B", kind=SaleRecord.Kind.SALE, status=SaleRecord.Status.SOLD, customer=customer_b, branch=self.branch_b, total=Decimal("900.00"), amount_paid=Decimal("900.00"))
        SalePayment.objects.create(sale=self.sale_a, method=SalePayment.Method.CASH, amount=Decimal("40.00"))
        SalePayment.objects.create(sale=sale_b, method=SalePayment.Method.CASH, amount=Decimal("900.00"))
        Lead.objects.create(full_name="Lead A", email="lead-a@example.com", branch=self.branch_a, assigned_advisor=self.user, status=Lead.Status.WON)
        Lead.objects.create(full_name="Lead B", email="lead-b@example.com", branch=self.branch_b, status=Lead.Status.WON)
        item = InventoryItem.objects.create(name="Filtro BI", sku="BI-FILTER", price=Decimal("5.00"))
        BranchStock.objects.create(item=item, branch=self.branch_a, quantity=Decimal("2.00"), minimum_stock=Decimal("3.00"))
        BranchStock.objects.create(item=item, branch=self.branch_b, quantity=Decimal("99.00"), minimum_stock=Decimal("3.00"))

    def test_bi_metrics_and_trends_are_branch_scoped(self):
        today = timezone.localdate()
        data = commercial_dashboard_data(self.user, {"start_date": today.replace(day=1), "end_date": today})
        self.assertEqual(data["metrics"]["total"], 1)
        self.assertEqual(data["metrics"]["sales_count"], 1)
        self.assertEqual(data["metrics"]["sales_total"], Decimal("100.00"))
        self.assertEqual(data["metrics"]["payments_total"], Decimal("40.00"))
        self.assertEqual(data["metrics"]["balance_total"], Decimal("60.00"))
        self.assertEqual(data["metrics"]["customers"], 1)
        self.assertEqual(data["metrics"]["stock_units"], Decimal("2.00"))
        self.assertEqual(data["metrics"]["low_stock"], 1)
        self.assertEqual(data["sales_trend"][0]["total"], Decimal("100.00"))
        self.assertEqual(data["branch_performance"][0]["branch_id"], self.branch_a.pk)

    def test_api_validates_scope_and_paginates_export_dataset(self):
        self.client.force_login(self.user)
        summary = self.client.get("/api/commercial-analytics/summary/")
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.json()["metrics"]["sales_total"], 100.0)
        self.assertEqual(self.client.get("/api/commercial-analytics/summary/", {"branch": self.branch_b.pk}).status_code, 400)
        self.assertEqual(self.client.get("/api/commercial-analytics/summary/", {"start_date": "bad"}).status_code, 400)
        dataset = self.client.get("/api/commercial-analytics/leads-dataset/", {"page_size": 1})
        self.assertEqual(dataset.status_code, 200)
        self.assertEqual(dataset.json()["count"], 1)
        self.assertEqual(dataset.json()["results"][0]["branch_id"], self.branch_a.pk)
