"""ES: Este módulo especifica regresiones ejecutables para el dominio de reportes.

EN: This module specifies executable regressions for the reports domain.

Contexto existente / Existing context:
Regression coverage for finance scope v130 in the reports domain.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.audit.models import AuditLog
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.documents.models import PrivateDocument
from apps.invoices.models import InvoiceRecord
from apps.reports import selectors
from apps.reports.forms import ReportFilterForm
from apps.reports.models import ReportExportJob
from apps.sales.models import SalePayment, SaleRecord
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel


class FinanceReportScopeTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            legal_name="Reportes Scope S.A.",
            commercial_name="Reportes Scope",
            ruc="0999999998001",
        )
        self.branch_a = Branch.objects.create(
            company=self.company,
            name="Sucursal A",
            code="report-a",
            city="Quito",
        )
        self.branch_b = Branch.objects.create(
            company=self.company,
            name="Sucursal B",
            code="report-b",
            city="Guayaquil",
        )
        self.report_permission = PermissionCode.objects.create(
            module="reports",
            code="reports.view",
            name="Ver reportes",
        )
        self.export_permission = PermissionCode.objects.create(
            module="data",
            code="data.export",
            name="Exportar datos",
        )
        self.role = Role.objects.create(code="report_branch", name="Reportes por sucursal")
        self.role.permissions.add(self.report_permission)
        User = get_user_model()
        self.user = User.objects.create_user(
            username="report-a",
            email="report-a@example.com",
            password="pass12345",
        )
        self.global_user = User.objects.create_user(
            username="report-global",
            email="report-global@example.com",
            password="pass12345",
        )
        UserRole.objects.create(user=self.user, role=self.role, branch=self.branch_a)
        UserRole.objects.create(user=self.global_user, role=self.role, branch=None)

        customer_a = Customer.objects.create(
            first_name="Cliente",
            last_name="A",
            email="cliente-a@example.com",
            assigned_branch=self.branch_a,
        )
        customer_b = Customer.objects.create(
            first_name="Cliente",
            last_name="B",
            email="cliente-b@example.com",
            assigned_branch=self.branch_b,
        )
        brand = VehicleBrand.objects.create(name="Scope Motors")
        model = VehicleModel.objects.create(brand=brand, name="Scope One")
        vehicle_a = Vehicle.objects.create(
            brand=brand,
            model=model,
            branch=self.branch_a,
            year=2025,
            vin="REPORTSCOPEA001",
            public_slug="report-scope-a",
            status=Vehicle.Status.SOLD,
            price=Decimal("100.00"),
        )
        vehicle_b = Vehicle.objects.create(
            brand=brand,
            model=model,
            branch=self.branch_b,
            year=2025,
            vin="REPORTSCOPEB001",
            public_slug="report-scope-b",
            status=Vehicle.Status.SOLD,
            price=Decimal("900.00"),
        )
        self.sale_a = SaleRecord.objects.create(
            number="REPORT-SALE-A",
            kind=SaleRecord.Kind.SALE,
            status=SaleRecord.Status.SOLD,
            customer=customer_a,
            branch=self.branch_a,
            advisor=self.user,
            vehicle=vehicle_a,
            total=Decimal("100.00"),
            amount_paid=Decimal("40.00"),
            balance_due=Decimal("60.00"),
        )
        self.sale_b = SaleRecord.objects.create(
            number="REPORT-SALE-B",
            kind=SaleRecord.Kind.SALE,
            status=SaleRecord.Status.SOLD,
            customer=customer_b,
            branch=self.branch_b,
            advisor=self.global_user,
            vehicle=vehicle_b,
            total=Decimal("900.00"),
            amount_paid=Decimal("700.00"),
            balance_due=Decimal("200.00"),
        )
        SalePayment.objects.create(
            sale=self.sale_a,
            method=SalePayment.Method.CASH,
            amount=Decimal("40.00"),
        )
        SalePayment.objects.create(
            sale=self.sale_b,
            method=SalePayment.Method.TRANSFER,
            amount=Decimal("700.00"),
        )
        for suffix, branch, customer, sale, total in (
            ("A", self.branch_a, customer_a, self.sale_a, Decimal("100.00")),
            ("B", self.branch_b, customer_b, self.sale_b, Decimal("900.00")),
        ):
            InvoiceRecord.objects.create(
                number=f"REPORT-INVOICE-{suffix}",
                invoice_type=InvoiceRecord.InvoiceType.INVOICE,
                status=InvoiceRecord.Status.ISSUED,
                sale=sale,
                company=self.company,
                branch=branch,
                customer=customer,
                customer_name=customer.display_name,
                issue_date=timezone.localdate(),
                total=total,
                balance_due=total,
            )
            PrivateDocument.objects.create(
                title=f"Documento {suffix}",
                document_type=PrivateDocument.DocumentType.INVOICE,
                file=f"private/report-{suffix.lower()}.pdf",
                status=PrivateDocument.Status.PENDING_REVIEW,
                branch=branch,
            )
            AuditLog.objects.create(
                action=f"reports.scope.{suffix.lower()}",
                branch=branch,
                object_repr=f"Registro {suffix}",
            )

    def _filters(self):
        today = timezone.localdate()
        return {"start_date": today.replace(day=1), "end_date": today, "branch": None, "q": ""}

    def test_branch_assignment_scopes_filters_finance_and_activity(self):
        form = ReportFilterForm(user=self.user)
        self.assertQuerySetEqual(form.fields["branch"].queryset, [self.branch_a])
        self.assertQuerySetEqual(form.fields["seller"].queryset, [self.user])
        self.assertQuerySetEqual(form.fields["vehicle"].queryset, [self.sale_a.vehicle])

        context = selectors.executive_context(self._filters(), self.user)
        self.assertEqual(context["metrics"]["sales_count"], 1)
        self.assertEqual(context["metrics"]["sales_total"], Decimal("100.00"))
        self.assertEqual(context["metrics"]["payments_total"], Decimal("40.00"))
        self.assertEqual(context["metrics"]["pending_balance"], Decimal("60.00"))
        self.assertEqual(context["metrics"]["invoices_total"], Decimal("100.00"))
        self.assertEqual(context["metrics"]["pending_documents"], 1)
        self.assertEqual(context["seller_summary"][0]["advisor_id"], self.user.pk)
        self.assertEqual(context["seller_summary"][0]["total"], Decimal("100.00"))
        self.assertEqual(list(selectors.activity_queryset(self._filters(), self.user).values_list("action", flat=True)), ["reports.scope.a"])

        global_context = selectors.executive_context(self._filters(), self.global_user)
        self.assertEqual(global_context["metrics"]["sales_count"], 2)
        self.assertEqual(global_context["metrics"]["payments_total"], Decimal("740.00"))

    def test_html_and_api_do_not_expose_another_branch(self):
        self.client.force_login(self.user)
        detail = self.client.get(reverse("reports_internal:detail", kwargs={"report_type": "sales"}))
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "REPORT-SALE-A")
        self.assertNotContains(detail, "REPORT-SALE-B")
        self.assertNotContains(detail, ">CSV<")
        self.assertContains(detail, "Rendimiento por vendedor")

        summary = self.client.get("/api/reports/summary/")
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.json()["sales_total"], 100.0)
        self.assertEqual(summary.json()["payments_total"], 40.0)
        seller_summary = self.client.get("/api/reports/summary/", {"seller": self.user.pk})
        self.assertEqual(seller_summary.status_code, 200)
        self.assertEqual(seller_summary.json()["sales_total"], 100.0)
        sale_detail = self.client.get("/api/reports/sales/", {"sale_status": SaleRecord.Status.SOLD, "page_size": 1})
        self.assertEqual(sale_detail.status_code, 200)
        self.assertEqual(len(sale_detail.json()["rows"]), 1)
        self.assertEqual(sale_detail.json()["rows"][0][0], "REPORT-SALE-A")
        self.assertFalse(sale_detail.json()["pagination"]["has_next"])
        branch_detail = self.client.get("/api/reports/branches/")
        self.assertEqual(branch_detail.status_code, 200)
        self.assertEqual(branch_detail.json()["rows"][0][0], "Sucursal A")
        self.assertEqual(self.client.get("/api/reports/summary/", {"branch": self.branch_b.pk}).status_code, 400)
        self.assertEqual(self.client.get("/api/reports/summary/", {"vehicle": self.sale_b.vehicle_id}).status_code, 400)
        self.assertEqual(self.client.get("/api/reports/sales/", {"page_size": 201}).status_code, 400)
        self.assertEqual(self.client.get("/api/reports/summary/", {"start_date": "invalid"}).status_code, 400)
        self.assertEqual(
            self.client.get("/api/reports/summary/", {"start_date": "2026-02-02", "end_date": "2026-02-01"}).status_code,
            400,
        )
        self.assertEqual(self.client.get("/api/reports/not-a-report/").status_code, 404)

    def test_export_requires_explicit_permission_and_remains_scoped(self):
        self.client.force_login(self.user)
        url = reverse(
            "reports_internal:export",
            kwargs={"report_type": "sales", "export_format": "csv"},
        )
        denied = self.client.get(url)
        self.assertEqual(denied.status_code, 403)
        self.assertFalse(ReportExportJob.objects.exists())

        self.role.permissions.add(self.export_permission)
        exported = self.client.get(url)
        self.assertEqual(exported.status_code, 200)
        self.assertIn(b"REPORT-SALE-A", exported.content)
        self.assertNotIn(b"REPORT-SALE-B", exported.content)
        self.assertTrue(
            ReportExportJob.objects.filter(
                report_type="sales",
                export_format="csv",
                status=ReportExportJob.Status.COMPLETED,
            ).exists()
        )
