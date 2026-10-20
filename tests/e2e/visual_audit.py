# -*- coding: utf-8 -*-
"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Auditoría visual D6 (no forma parte de la suite E2E de producto).

Recorre los roles reales de la semilla, abre sus rutas accesibles en
1440x900 / 768x1024 / 390x844 con tema Light y Dark, y comprueba:

* sin scroll horizontal (overflow) en ningún viewport,
* sin errores JS no capturados,
* el tema aplicado coincide con el solicitado,
* evidencia PNG por rol/ruta/viewport/tema.

Uso (QA runner):
  VINOVA_E2E_ACTIVE=1 VINOVA_E2E_ARTIFACT_ROOT=<dir>     python -m pytest -q tests/e2e/visual_audit.py -s
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.accounts.management.commands.seed_roles import PERMISSIONS, ROLE_DEFINITIONS
from apps.accounts.models import PermissionCode, Role, User, UserRole
from apps.customers.models import Customer
from tests.e2e.helpers.auth import login as perform_login
from tests.e2e.helpers.base import VinovaE2EBase

pytestmark = pytest.mark.e2e

VIEWPORTS = {
    "1440x900": (1440, 900),
    "768x1024": (768, 1024),
    "390x844": (390, 844),
}

THEMES = ("light", "dark")

# (slug, ruta, permisos requeridos, alcance)
ROUTE_MATRIX = [
    ("vehicles", "/dashboard/vehicles/", ("vehicles.view", "vehicles.manage"), "branch"),
    ("customers", "/dashboard/customers/", ("customers.view", "customers.manage"), "branch"),
    ("leads", "/dashboard/leads/", ("leads.view",), "branch"),
    ("inventory", "/dashboard/inventory/", ("inventory.view", "inventory.manage_stock"), "branch"),
    ("sales", "/dashboard/sales/", ("sales.quote", "sales.reserve", "sales.sell"), "branch"),
    ("invoices", "/dashboard/invoices/", ("invoices.view", "invoices.issue", "invoices.manage"), "branch"),
    ("documents", "/dashboard/documents/", ("documents.view", "documents.manage"), "branch"),
    ("notifications", "/dashboard/notifications/", ("notifications.view", "notifications.send"), "branch"),
    ("reports", "/dashboard/reports/", ("reports.view",), "branch"),
    ("imports", "/dashboard/imports/", ("imports.manage",), "branch"),
    ("analytics", "/dashboard/analytics/", ("analytics.view",), "branch"),
    ("audit", "/dashboard/audit/", ("audit.view",), "branch"),
    ("privacy", "/dashboard/privacy/", ("privacy.view",), "branch"),
    ("security", "/dashboard/security/", ("security.view",), "branch"),
    ("help", "/dashboard/help/", ("help.view",), "branch"),
]

DASHBOARD_BY_ROLE = {
    "superadmin": "/dashboard/admin/",
    "admin_general": "/dashboard/admin/",
    "admin_sucursal": "/dashboard/branch/",
    "gerente_comercial": "/dashboard/commercial/",
    "jefe_inventario": "/dashboard/inventory-home/",
    "vendedor": "/dashboard/seller/",
    "asesor_postventa": "/dashboard/support/",
    "facturacion": "/dashboard/billing/",
    "bodega": "/dashboard/inventory-home/",
    "marketing": "/dashboard/marketing/",
    "soporte_cliente": "/dashboard/support/",
    "auditor": "/dashboard/auditor/",
    "cliente": "/mi-cuenta/",
}

MAX_EXTRA_ROUTES = 5


def _overflow_report(page) -> list[str]:
    return page.evaluate(
        """
        () => {
          const doc = document.documentElement;
          const vw = doc.clientWidth;
          if (doc.scrollWidth <= vw + 1) return [];
          const out = [];
          for (const el of document.querySelectorAll('body *')) {
            const rect = el.getBoundingClientRect();
            if (rect.width > 0 && rect.right > vw + 1) {
              const cls = (typeof el.className === 'string' ? el.className : '').slice(0, 60);
              out.push(`${el.tagName.toLowerCase()}${cls ? '.' + cls.replace(/\\s+/g, '.') : ''} right=${Math.round(rect.right)}`);
            }
            if (out.length >= 6) break;
          }
          return out;
        }
        """
    )


class TestVisualAudit(VinovaE2EBase):
    def _out_dir(self) -> Path:
        base = Path(os.getenv("VINOVA_E2E_ARTIFACT_ROOT", "run/qa/e2e"))
        out = base / "d6-visual-audit"
        out.mkdir(parents=True, exist_ok=True)
        return out

    def _apply_theme(self, theme: str) -> None:
        self.page.evaluate("(t) => localStorage.setItem('vinova-theme', t)", theme)
        self.page.reload(wait_until="load")
        self.page.wait_for_load_state("networkidle")

    def _capture(self, dest: Path, name: str, *, full: bool = True) -> None:
        dest.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(dest / f"{name}.png"), full_page=full, timeout=120_000)

    def test_d6_visual_audit_by_role(self):
        call_command("seed_roles")
        for module, code, label in PERMISSIONS:
            PermissionCode.objects.get_or_create(code=code, defaults={"module": module, "name": label})

        out_root = self._out_dir()
        results: list[dict] = []
        failures: list[str] = []
        js_errors: list[str] = []

        def on_page_error(exc):
            js_errors.append(str(exc))

        self.page.on("pageerror", on_page_error)

        for role_code, (role_name, _level) in ROLE_DEFINITIONS.items():
            user = User.objects.create_user(
                username=f"visual-{role_code}",
                email=f"visual-{role_code}@example.com",
                password=self.password,
                branch=self.branch,
            )
            role = Role.objects.get(code=role_code)
            assignment_branch = None if role_code in {"superadmin", "admin_general"} else self.branch
            UserRole.objects.create(user=user, role=role, branch=assignment_branch)
            if role_code == "cliente":
                Customer.objects.create(
                    account=user,
                    first_name="Cliente",
                    last_name="Auditoría visual",
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
            else:
                self.login(user)

            accessible = [
                (slug, path)
                for slug, path, codes, scope in ROUTE_MATRIX
                if any(user.has_perm_code(code) for code in codes)
                and (scope != "global" or role_code in {"superadmin", "admin_general"})
            ]
            accessible = accessible[:MAX_EXTRA_ROUTES]
            targets = [("dashboard", DASHBOARD_BY_ROLE[role_code])] + accessible

            for target_index, (slug, path) in enumerate(targets):
                response = self.page.goto(f"{self.live_server_url}{path}", wait_until="load")
                status = response.status if response else 0
                if status != 200:
                    failures.append(f"{role_code}/{slug}: HTTP {status} en {path}")
                    continue
                self.page.wait_for_load_state("networkidle")

                # Tema en todas las vistas; viewports completos en el dashboard.
                theme_matrix = THEMES if target_index == 0 else ("light", "dark")
                for theme in theme_matrix:
                    self._apply_theme(theme)
                    applied = self.page.get_attribute("html", "data-theme")
                    if applied not in {theme, "auto"}:
                        failures.append(f"{role_code}/{slug}: data-theme={applied} (esperaba {theme})")

                    viewport_keys = list(VIEWPORTS) if target_index == 0 else ["1440x900", "390x844"]
                    for viewport_key in viewport_keys:
                        width, height = VIEWPORTS[viewport_key]
                        self.page.set_viewport_size({"width": width, "height": height})
                        self.page.wait_for_timeout(250)

                        overflow = _overflow_report(self.page)
                        if overflow:
                            failures.append(
                                f"{role_code}/{slug}/{viewport_key}/{theme}: overflow horizontal -> {overflow}"
                            )

                        role_dir = out_root / role_code / slug / theme / viewport_key
                        self._capture(role_dir, "shot", full=target_index == 0)
                        results.append(
                            {
                                "role": role_code,
                                "role_name": role_name,
                                "route": slug,
                                "path": path,
                                "theme": theme,
                                "viewport": viewport_key,
                                "overflow": overflow,
                            }
                        )

                    self.page.set_viewport_size({"width": 1440, "height": 900})

            if js_errors:
                failures.append(f"{role_code}: errores JS no capturados: {js_errors[:3]}")
                js_errors.clear()

        report = {
            "checkpoints": len(results),
            "failures": failures,
            "shots": sorted(
                str(p.relative_to(out_root)) for p in out_root.rglob("*.png")
            ),
        }
        (out_root / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        assert not failures, "Fallos de auditoría visual:\n" + "\n".join(failures)
        assert len(results) > 100, f"solo {len(results)} checkpoints capturados"

    # ------------------------------------------------------------------
    # Estados de UI: formulario inválido, vacío, sin resultados, modal y 403.
    # ------------------------------------------------------------------

    def _capture_state(
        self, out_root: Path, name: str, act, failures: list[str], notes: list[str]
    ) -> None:
        for theme in THEMES:
            if not self.page.url.startswith(self.live_server_url):
                self.page.goto(f"{self.live_server_url}/accounts/login/", wait_until="load")
            self.page.evaluate("(t) => localStorage.setItem('vinova-theme', t)", theme)
            act()
            applied = self.page.get_attribute("html", "data-theme")
            if applied is None:
                notes.append(
                    f"states/{name}: sin data-theme, la vista no carga theme.js "
                    "(página sin plantilla propia)"
                )
            elif applied != theme:
                failures.append(f"states/{name}: data-theme={applied} (esperaba {theme})")

            for viewport_key in ("1440x900", "390x844"):
                width, height = VIEWPORTS[viewport_key]
                self.page.set_viewport_size({"width": width, "height": height})
                self.page.wait_for_timeout(250)

                overflow = _overflow_report(self.page)
                if overflow:
                    failures.append(f"states/{name}/{viewport_key}/{theme}: overflow horizontal -> {overflow}")

                self._capture(out_root / "states" / name / theme / viewport_key, "shot")

            self.page.set_viewport_size({"width": 1440, "height": 900})

    def test_d6_visual_states(self):
        call_command("seed_roles")
        for module, code, label in PERMISSIONS:
            PermissionCode.objects.get_or_create(code=code, defaults={"module": module, "name": label})

        out_root = self._out_dir()
        failures: list[str] = []
        js_errors: list[str] = []
        self.page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        warehouse_user = User.objects.create_user(
            username="visual-states-bodega",
            email="visual-states-bodega@example.com",
            password=self.password,
            branch=self.branch,
        )
        UserRole.objects.create(
            user=warehouse_user, role=Role.objects.get(code="bodega"), branch=self.branch
        )

        def as_admin() -> None:
            self.page.context.clear_cookies()
            self.login(self.admin)

        def as_bodega() -> None:
            self.page.context.clear_cookies()
            perform_login(self.page, self.live_server_url, warehouse_user, self.password)

        def form_errors() -> None:
            as_admin()
            self.page.goto(f"{self.live_server_url}/dashboard/customers/new/", wait_until="load")
            self.page.wait_for_load_state("networkidle")
            self.page.get_by_role("button", name="Guardar cliente").click()
            self.page.wait_for_selector(".field-error", timeout=15_000)

        def empty_list() -> None:
            as_admin()
            Customer.objects.all().delete()
            self.page.goto(f"{self.live_server_url}/dashboard/customers/", wait_until="load")
            self.page.wait_for_selector(".empty-table-row", timeout=15_000)

        def no_results() -> None:
            as_admin()
            self.page.goto(
                f"{self.live_server_url}/dashboard/customers/?q=zzzzzznope", wait_until="load"
            )
            self.page.wait_for_selector(".empty-table-row", timeout=15_000)

        def vehicle_modal() -> None:
            self.page.context.clear_cookies()
            self.page.goto(f"{self.live_server_url}/vehicles/", wait_until="load")
            self.page.wait_for_load_state("networkidle")
            self.page.locator("button:has-text('Ver ficha')").first.click()
            self.page.wait_for_selector("[data-vinova-modal]", timeout=15_000)

        def catalog_empty() -> None:
            self.page.context.clear_cookies()
            self.page.goto(f"{self.live_server_url}/vehicles/?marca=999999", wait_until="load")
            self.page.wait_for_selector(".catalog-empty", timeout=15_000)

        def denied_403() -> None:
            as_bodega()
            response = self.page.goto(
                f"{self.live_server_url}/dashboard/audit/", wait_until="load"
            )
            status = response.status if response else 0
            assert status == 403, f"/dashboard/audit/ como bodega devolvió HTTP {status}"

        states = [
            ("form-errors", form_errors),
            ("empty-list", empty_list),
            ("search-no-results", no_results),
            ("vehicle-modal", vehicle_modal),
            ("catalog-empty", catalog_empty),
            ("denied-403", denied_403),
        ]
        notes: list[str] = []
        for name, act in states:
            self._capture_state(out_root, name, act, failures, notes)

        if js_errors:
            failures.append(f"errores JS no capturados: {js_errors[:5]}")

        report = {
            "states": [name for name, _ in states],
            "checkpoints": len(states) * len(THEMES) * 2,
            "failures": failures,
            "notes": sorted(set(notes)),
            "shots": sorted(str(p.relative_to(out_root / "states")) for p in (out_root / "states").rglob("*.png")),
        }
        (out_root / "states_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        assert not failures, "Fallos de estados visuales:\n" + "\n".join(failures)
