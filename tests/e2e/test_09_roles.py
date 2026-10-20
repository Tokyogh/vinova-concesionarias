"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for 09 roles in the e2e domain.
"""

from __future__ import annotations

import pytest
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse

from apps.accounts.management.commands.seed_roles import ROLE_DEFINITIONS, PERMISSIONS
from apps.accounts.models import PermissionCode, Role, User, UserRole
from apps.branches.models import Branch
from apps.customers.models import Customer
from apps.vehicles.models import Vehicle
from tests.e2e.helpers.base import VinovaE2EBase

pytestmark = pytest.mark.e2e


class TestRoleAndPermissionBoundaries(VinovaE2EBase):
    def test_09_role_and_permission_boundaries(self):
        permission = PermissionCode.objects.create(module="sales", code="sales.quote", name="Cotizar")
        dashboard_permission = PermissionCode.objects.create(module="dashboard", code="dashboard.view", name="Dashboard")
        role = Role.objects.create(code="vendedor-e2e", name="Vendedor E2E")
        role.permissions.add(permission, dashboard_permission)
        seller = User.objects.create_user(
            username="seller-e2e",
            email="seller.e2e@example.com",
            password=self.password,
            branch=self.branch,
        )
        UserRole.objects.create(user=seller, role=role, branch=self.branch)
        self.login(seller)
        response = self.page.goto(f"{self.live_server_url}/dashboard/sales/")
        assert response is not None and response.status == 200
        response = self.page.goto(f"{self.live_server_url}/dashboard/security/")
        assert response is not None and response.status == 403
        response = self.page.goto(f"{self.live_server_url}/dashboard/quality/")
        assert response is not None and response.status == 403

    @override_settings(VINOVA_MODULE_POST_SALES_ENABLED=False)
    def test_seeded_roles_dashboard_routes_and_branch_idor(self):
        call_command("seed_roles")
        for module, code, name in PERMISSIONS:
            PermissionCode.objects.get_or_create(code=code, defaults={"module": module, "name": name})

        remote_branch = Branch.objects.create(
            company=self.company,
            name="Sucursal QA remota",
            code="QA-REM",
            branch_type=Branch.BranchType.DEALERSHIP,
            city="Guayaquil",
        )
        remote_vehicle = Vehicle.objects.create(
            brand=self.brand,
            model=self.vehicle_model,
            branch=remote_branch,
            year=2025,
            version="Remoto QA",
            vin="VINQA000000000002",
            public_slug="foton-tunland-qa-remoto",
            status=Vehicle.Status.AVAILABLE,
            price="34000.00",
        )
        route_permissions = [
            ("vehicles", "/dashboard/vehicles/", ("vehicles.view", "vehicles.manage")),
            ("customers", "/dashboard/customers/", ("customers.view", "customers.manage")),
            ("leads", "/dashboard/leads/", ("leads.view",)),
            ("inventory", "/dashboard/inventory/", ("inventory.view", "inventory.manage_stock")),
            ("sales", "/dashboard/sales/", ("sales.quote", "sales.reserve", "sales.sell")),
            ("invoices", "/dashboard/invoices/", ("invoices.view", "invoices.issue", "invoices.manage")),
            ("documents", "/dashboard/documents/", ("documents.view", "documents.manage", "documents.download_private")),
            ("notifications", "/dashboard/notifications/", ("notifications.view", "notifications.send")),
            ("reports", "/dashboard/reports/", ("reports.view",)),
            ("imports", "/dashboard/imports/", ("imports.manage",)),
            ("analytics", "/dashboard/analytics/", ("analytics.view",)),
            ("audit", "/dashboard/audit/", ("audit.view",)),
            ("continuity", "/dashboard/continuity/", ("continuity.view",), "global"),
            ("privacy", "/dashboard/privacy/", ("privacy.view",)),
            ("integrations", "/dashboard/integrations/", ("integrations.view", "integrations.manage")),
            ("enterprise", "/dashboard/company/", ("enterprise.manage",), "global"),
            ("sri", "/dashboard/company/sri/", ("sri.manage",), "global"),
            ("security", "/dashboard/security/", ("security.view",)),
            ("quality", "/dashboard/quality/", ("quality.view",), "global"),
            ("help", "/dashboard/help/", ("help.view",)),
            ("branches", "/branches/", ("branches.manage",)),
            ("companies", "/companies/", ("companies.manage",), "global"),
            ("accounts", "/accounts/users/", ("accounts.manage_users",)),
        ]

        for role_code, (role_name, _level) in ROLE_DEFINITIONS.items():
            role = Role.objects.get(code=role_code)
            user = User.objects.create_user(
                username=f"role-matrix-{role_code}",
                email=f"role-matrix-{role_code}@example.com",
                password=self.password,
                branch=self.branch,
            )
            assignment_branch = None if role_code in {"superadmin", "admin_general"} else self.branch
            UserRole.objects.create(user=user, role=role, branch=assignment_branch)
            if role_code == "cliente":
                Customer.objects.create(
                    account=user,
                    first_name="Cliente",
                    last_name="Matriz E2E",
                    email=user.email,
                    assigned_branch=self.branch,
                    status=Customer.Status.ACTIVE,
                )
            self.page.context.clear_cookies()

            if role_code == "cliente":
                self.page.goto(f"{self.live_server_url}/accounts/login/")
                self.page.locator("input[name='username']").fill(user.username)
                self.page.locator("input[name='password']").fill(self.password)
                self.page.get_by_role("button", name="Ingresar").click()
                self.page.wait_for_load_state("networkidle")
                assert "/mi-cuenta/" in self.page.url
            else:
                self.login(user)
                page_response = self.page.goto(f"{self.live_server_url}/dashboard/")
                assert page_response is not None and page_response.status == 200, role_name

            evidence_dir = self.artifact_root / "role-matrix" / role_code
            evidence_dir.mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(evidence_dir / "dashboard.png"), full_page=True)

            for route in route_permissions:
                module, path, required_codes = route[:3]
                scope = route[3] if len(route) == 4 else "branch"
                response = self.page.goto(f"{self.live_server_url}{path}")
                assert response is not None, f"{role_code}: sin respuesta en {path}"
                allowed = role_code != "cliente" and any(user.has_perm_code(code) for code in required_codes)
                if scope == "global":
                    allowed = allowed and role_code in {"superadmin", "admin_general"}
                expected = 200 if allowed else 403
                assert response.status == expected, f"{role_code} → {module}: esperaba {expected}, recibió {response.status}"

            if any(user.has_perm_code(code) for code in ("vehicles.view", "vehicles.manage")):
                own_detail = self.page.goto(
                    f"{self.live_server_url}{reverse('vehicles_internal:detail', kwargs={'pk': self.vehicle.pk})}"
                )
                remote_detail = self.page.goto(
                    f"{self.live_server_url}{reverse('vehicles_internal:detail', kwargs={'pk': remote_vehicle.pk})}"
                )
                globally_scoped = role_code in {"superadmin", "admin_general"}
                assert own_detail is not None and own_detail.status == 200, role_code
                assert remote_detail is not None and remote_detail.status == (200 if globally_scoped else 404), role_code

            post_sales = self.page.goto(f"{self.live_server_url}/dashboard/post-sales/")
            assert post_sales is not None and post_sales.status == 404, role_code
