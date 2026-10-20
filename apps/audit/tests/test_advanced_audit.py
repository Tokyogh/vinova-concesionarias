"""ES: Este módulo especifica regresiones ejecutables para el dominio de auditoría.

EN: This module specifies executable regressions for the audit domain.

Contexto existente / Existing context:
Regression coverage for advanced audit in the audit domain.
"""

from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.audit.context import reset_audit_context, set_audit_context
from apps.audit.models import AuditLog, SecurityAlert
from apps.audit.services import audit_log, verify_audit_chain
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel


class AdvancedAuditTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.company = Company.objects.create(legal_name="Vinova Ecuador S.A.", commercial_name="Vinova", ruc="0999999999001")
        self.branch = Branch.objects.create(company=self.company, name="Quito Norte", code="quito-norte", city="Quito")
        self.user = User.objects.create_user(username="auditor", email="auditor@example.com", password="pass12345", branch=self.branch)
        self.viewer = User.objects.create_user(username="viewer", email="viewer@example.com", password="pass12345")
        perms = {}
        for code in ("audit.view", "audit.export", "audit.manage_alerts"):
            perms[code] = PermissionCode.objects.create(module="audit", code=code, name=code)
        role = Role.objects.create(code="audit-manager", name="Gestor de auditoría", level=5)
        role.permissions.set(perms.values())
        UserRole.objects.create(user=self.user, role=role, branch=None)
        self.brand = VehicleBrand.objects.create(name="Chevrolet")
        self.model = VehicleModel.objects.create(brand=self.brand, name="Camaro")
        self.vehicle = Vehicle.objects.create(
            brand=self.brand,
            model=self.model,
            year=2025,
            public_slug="camaro-audit-test",
        )

    def test_audit_log_captures_context_redacts_secrets_and_hashes(self):
        token = set_audit_context(
            {
                "request_id": "11111111-1111-1111-1111-111111111111",
                "ip_address": "127.0.0.1",
                "user_agent": "pytest",
                "http_method": "POST",
                "request_path": "/dashboard/vehicles/1/edit/",
                "branch": self.branch,
            }
        )
        try:
            log = audit_log(
                user=self.user,
                action="vehicles.update",
                target=self.vehicle,
                before={"price": "100", "password": "secret"},
                after={"price": "120", "api_token": "hidden"},
            )
        finally:
            reset_audit_context(token)

        self.assertEqual(log.ip_address, "127.0.0.1")
        self.assertEqual(log.branch, self.branch)
        self.assertEqual(log.request_path, "/dashboard/vehicles/1/edit/")
        self.assertEqual(log.before["password"], "[REDACTADO]")
        self.assertEqual(log.after["api_token"], "[REDACTADO]")
        self.assertTrue(log.entry_hash)
        self.assertEqual(log.previous_hash, "")
        self.assertTrue(log.role_snapshot)
        self.assertTrue(verify_audit_chain()["valid"])

    def test_integrity_verification_detects_tampering(self):
        first = audit_log(user=self.user, action="vehicles.create", target=self.vehicle, after={"price": "100"})
        second = audit_log(user=self.user, action="vehicles.update", target=self.vehicle, before={"price": "100"}, after={"price": "120"})
        self.assertEqual(second.previous_hash, first.entry_hash)
        self.assertTrue(verify_audit_chain(strict_links=True)["valid"])

        AuditLog.objects.filter(pk=second.pk).update(after={"price": "999999"})
        result = verify_audit_chain(strict_links=True)
        self.assertFalse(result["valid"])
        self.assertEqual(result["issues"][0]["event_id"], str(second.event_id))

    def test_high_risk_event_creates_security_alert(self):
        log = audit_log(
            user=self.user,
            action="security.permission_denied",
            after={"status_code": 403},
        )
        alert = SecurityAlert.objects.get(audit_log=log)
        self.assertEqual(alert.status, SecurityAlert.Status.OPEN)
        self.assertEqual(alert.severity, AuditLog.Severity.HIGH)

    def test_audit_pages_require_permission(self):
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("audit_internal:list"))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(AuditLog.objects.filter(action="security.permission_denied").exists())

        self.client.force_login(self.user)
        response = self.client.get(reverse("audit_internal:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Auditoría avanzada")

    def test_export_xlsx_and_alert_resolution(self):
        audit_log(user=self.user, action="vehicles.update", target=self.vehicle, after={"status": "available"})
        alert_log = audit_log(user=self.user, action="security.permission_denied", after={"status_code": 403})
        alert = SecurityAlert.objects.get(audit_log=alert_log)

        self.client.force_login(self.user)
        response = self.client.get(reverse("audit_internal:export") + "?format=xlsx")
        self.assertEqual(response.status_code, 200)
        workbook = load_workbook(BytesIO(response.content))
        self.assertEqual(workbook.active.title, "auditoria")
        self.assertTrue(AuditLog.objects.filter(action="audit.export").exists())

        response = self.client.post(
            reverse("audit_internal:alert_update", kwargs={"alert_id": alert.alert_id}),
            {"status": SecurityAlert.Status.RESOLVED, "resolution_notes": "Revisado y cerrado."},
        )
        self.assertEqual(response.status_code, 302)
        alert.refresh_from_db()
        self.assertEqual(alert.status, SecurityAlert.Status.RESOLVED)
        self.assertEqual(alert.resolved_by, self.user)
        self.assertIsNotNone(alert.resolved_at)

    def test_read_only_api_obeys_permission(self):
        log = audit_log(user=self.user, action="vehicles.update", target=self.vehicle, after={"status": "available"})
        self.client.force_login(self.user)
        response = self.client.get("/api/audit-logs/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(log.event_id))

        self.client.force_login(self.viewer)
        response = self.client.get("/api/audit-logs/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)
