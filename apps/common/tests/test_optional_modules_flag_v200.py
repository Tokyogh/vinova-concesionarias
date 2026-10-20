"""ES: Este módulo especifica regresiones ejecutables para el dominio de infraestructura compartida.

EN: This module specifies executable regressions for the common domain.

Contexto existente / Existing context:
Regression coverage for optional modules flag v200 in the common domain.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company


def _mk_permission(module, code):
    return PermissionCode.objects.get_or_create(module=module, code=code, defaults={"name": code})[0]


def _user_with_post_sales_perm():
    company = Company.objects.create(legal_name="Flags S.A.", commercial_name="Flags", ruc="1799999999003")
    branch = Branch.objects.create(company=company, name="Sede", code="FLAG-1", city="Quito")
    role = Role.objects.create(code="post_sales_flag", name="Postventa flag")
    role.permissions.add(_mk_permission("post_sales", "post_sales.manage"), _mk_permission("dashboard", "dashboard.view"))
    user = get_user_model().objects.create_user(username="post_flag", email="postflag@example.com", password="x")
    UserRole.objects.create(user=user, role=role, branch=branch)
    return user


def _user_with_dashboard_only():
    company = Company.objects.create(legal_name="Flags B S.A.", commercial_name="Flags B", ruc="1799999999004")
    branch = Branch.objects.create(company=company, name="Sede B", code="FLAG-2", city="Quito")
    role = Role.objects.create(code="dash_only", name="Solo panel")
    role.permissions.add(_mk_permission("dashboard", "dashboard.view"))
    user = get_user_model().objects.create_user(username="dash_only", email="dashonly@example.com", password="x")
    UserRole.objects.create(user=user, role=role, branch=branch)
    return user


class OptionalModuleOffTests(TestCase):
    def test_sidebar_hides_post_sales_when_module_off(self):
        self.client.force_login(_user_with_post_sales_perm())
        response = self.client.get(reverse("dashboard:staff_home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Postventa")

    @override_settings(VINOVA_MODULE_POST_SALES_ENABLED=True)
    def test_sidebar_post_sales_blocked_for_user_without_perm(self):
        self.client.force_login(_user_with_dashboard_only())
        response = self.client.get(reverse("dashboard:staff_home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Postventa")

    @override_settings(VINOVA_MODULE_POST_SALES_ENABLED=True)
    def test_sidebar_shows_post_sales_when_module_on_and_perm(self):
        self.client.force_login(_user_with_post_sales_perm())
        response = self.client.get(reverse("dashboard:staff_home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{reverse("post_sales:list")}"')
        self.assertContains(response, "Postventa")
