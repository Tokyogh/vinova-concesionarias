"""ES: Este módulo especifica regresiones ejecutables para el dominio de reportes.

EN: This module specifies executable regressions for the reports domain.

Contexto existente / Existing context:
Regression coverage for reports enterprise in the reports domain.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.invoices.models import InvoiceRecord
from apps.reports.models import ReportExportJob
from apps.sales.models import SaleRecord
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel


class ReportsEnterpriseTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(username="admin", email="admin@example.com", password="pass12345")
        self.company = Company.objects.create(legal_name="Vinova Ecuador S.A.", commercial_name="Vinova", ruc="0999999999001")
        self.branch = Branch.objects.create(company=self.company, name="Quito Norte", code="quito-norte", city="Quito")
        customer = Customer.objects.create(first_name="Carlos", last_name="Paz", email="carlos@example.com", assigned_branch=self.branch)
        brand = VehicleBrand.objects.create(name="GMC")
        model = VehicleModel.objects.create(brand=brand, name="Canyon")
        vehicle = Vehicle.objects.create(brand=brand, model=model, branch=self.branch, year=2023, vin="VINREPORT001", public_slug="gmc-canyon-report", price=Decimal("45000.00"))
        self.sale = SaleRecord.objects.create(number="SALE-RPT-001", kind=SaleRecord.Kind.SALE, status=SaleRecord.Status.SOLD, customer=customer, branch=self.branch, vehicle=vehicle, total=Decimal("45000.00"), amount_paid=Decimal("10000.00"), balance_due=Decimal("35000.00"))
        InvoiceRecord.objects.create(number="FAC-RPT-001", invoice_type=InvoiceRecord.InvoiceType.INVOICE, status=InvoiceRecord.Status.ISSUED, sale=self.sale, company=self.company, branch=self.branch, customer=customer, customer_name=customer.display_name, customer_document="", issue_date=timezone.localdate(), total=Decimal("45000.00"), amount_paid=Decimal("10000.00"), balance_due=Decimal("35000.00"))

    def test_reports_home_requires_auth_and_renders_for_superuser(self):
        response = self.client.get(reverse("reports_internal:home"))
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.user)
        response = self.client.get(reverse("reports_internal:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reportes empresariales")
        self.assertContains(response, "Ventas por fecha")

    def test_sales_report_detail_and_csv_export(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("reports_internal:detail", kwargs={"report_type": "sales"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SALE-RPT-001")
        export = self.client.get(reverse("reports_internal:export", kwargs={"report_type": "sales", "export_format": "csv"}))
        self.assertEqual(export.status_code, 200)
        self.assertIn("text/csv", export["Content-Type"])
        self.assertIn(b"SALE-RPT-001", export.content)
        self.assertTrue(ReportExportJob.objects.filter(report_type="sales", export_format="csv", status=ReportExportJob.Status.COMPLETED).exists())

    def test_reports_api_summary(self):
        self.client.force_login(self.user)
        response = self.client.get("/api/reports/summary/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("sales_count", response.json())
