"""ES: Este módulo especifica regresiones ejecutables para el dominio de postventa.

EN: This module specifies executable regressions for the post sales domain.

Contexto existente / Existing context:
Regression coverage for post sales v140 in the post_sales domain.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.post_sales.models import ServiceOrder
from apps.post_sales.services import transition_service_order
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel


class PostSalesTests(TestCase):
    def setUp(self):
        company = Company.objects.create(legal_name="Postventa S.A.", commercial_name="Postventa", ruc="0999999997001")
        self.branch = Branch.objects.create(company=company, name="Taller", code="taller", city="Quito")
        other_branch = Branch.objects.create(company=company, name="Otro taller", code="otro-taller", city="Cuenca")
        permission = PermissionCode.objects.create(module="post_sales", code="post_sales.manage", name="Gestionar postventa")
        role = Role.objects.create(code="post_sales_test", name="Postventa test")
        role.permissions.add(permission)
        self.user = get_user_model().objects.create_user(username="postventa", email="postventa@example.com", password="x")
        UserRole.objects.create(user=self.user, role=role, branch=self.branch)
        customer = Customer.objects.create(first_name="Ana", last_name="Paz", email="ana-post@example.com", assigned_branch=self.branch)
        brand = VehicleBrand.objects.create(name="Post Brand")
        model = VehicleModel.objects.create(brand=brand, name="Post Model")
        vehicle = Vehicle.objects.create(brand=brand, model=model, branch=self.branch, year=2025, vin="POSTSALE001", public_slug="post-sale-001")
        self.order = ServiceOrder.objects.create(
            number="POST-001",
            branch=self.branch,
            customer=customer,
            vehicle=vehicle,
            description="Inspección solicitada por cliente",
            labor_cost=Decimal("10.00"),
            total_cost=Decimal("10.00"),
        )
        other_customer = Customer.objects.create(
            first_name="Cliente",
            last_name="Externo",
            email="externo-post@example.com",
            assigned_branch=other_branch,
        )
        other_vehicle = Vehicle.objects.create(
            brand=brand,
            model=model,
            branch=other_branch,
            year=2024,
            vin="POSTSALE002",
            public_slug="post-sale-002",
        )
        ServiceOrder.objects.create(
            number="POST-OTHER",
            branch=other_branch,
            customer=other_customer,
            vehicle=other_vehicle,
            description="No visible",
        )

    def test_disabled_module_blocks_direct_url(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("post_sales:list"))
        self.assertEqual(response.status_code, 404)

    @override_settings(VINOVA_MODULE_POST_SALES_ENABLED=True)
    def test_enabled_module_lists_and_transitions_with_history(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("post_sales:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "POST-001")
        self.assertNotContains(response, "POST-OTHER")
        line_response = self.client.post(
            reverse("post_sales:line_create", kwargs={"pk": self.order.pk}),
            {
                "line_type": "part",
                "description": "Filtro",
                "quantity": "2.00",
                "unit_cost": "7.50",
            },
        )
        self.assertEqual(line_response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.parts_cost, Decimal("15.00"))
        self.assertEqual(self.order.total_cost, Decimal("15.00"))
        transition_service_order(actor=self.user, order_id=self.order.pk, new_status=ServiceOrder.Status.SCHEDULED)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, ServiceOrder.Status.SCHEDULED)
        self.assertEqual(self.order.history.count(), 1)
