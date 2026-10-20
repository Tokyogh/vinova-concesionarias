"""ES: Este módulo especifica regresiones ejecutables para el dominio de cuentas.

EN: This module specifies executable regressions for the accounts domain.

Contexto existente / Existing context:
Regression coverage for deployment smoke roles in the accounts domain.
"""

from __future__ import annotations

import json

import pytest
from django.core.management import call_command

from apps.accounts.management.commands.seed_roles import PERMISSIONS, ROLE_DEFINITIONS, ROLE_PERMISSION_MAP as SEEDED_MAP
from apps.accounts.models import User
from apps.companies.models import Company
from apps.vehicles.models import VehicleBrand, VehicleModel
from tests.deployment_smoke.role_contract import ROLE_CODES, ROLE_PERMISSION_MAP

pytestmark = pytest.mark.django_db


def test_role_contract_matches_seed_roles():
    assert ROLE_CODES == list(ROLE_DEFINITIONS)
    all_permissions = {item[1] for item in PERMISSIONS}
    for role_code in ROLE_CODES:
        expected = all_permissions if role_code in {"superadmin", "admin_general"} else set(SEEDED_MAP[role_code])
        actual = all_permissions if "*" in ROLE_PERMISSION_MAP[role_code] else set(ROLE_PERMISSION_MAP[role_code])
        assert actual == expected


def test_role_accounts_can_be_provisioned_and_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("VINOVA_ENVIRONMENT", "test")
    monkeypatch.setenv("VINOVA_SMOKE_ALLOW_ROLE_PROVISION", "true")
    output = tmp_path / "roles.json"
    call_command("deployment_smoke_roles", "provision", run_id="abcdef123456", output=output, expires_hours=1)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert set(payload["accounts"]) == set(ROLE_CODES) | {"inactive"}
    assert payload["accounts"]["inactive"]["is_active"] is False
    assert User.objects.filter(username__startswith="smoke.role.abcdef123456.", is_active=True).count() == len(ROLE_CODES)
    company = Company.objects.get(email="smoke.roles.abcdef123456@vinova.invalid")
    assert len(company.ruc) == 13
    assert company.ruc.isdigit()
    assert VehicleBrand.objects.filter(name="SMOKE-abcdef123456", is_active=True).exists()
    assert VehicleModel.objects.filter(brand__name="SMOKE-abcdef123456", is_active=True).exists()

    call_command("deployment_smoke_roles", "disable", run_id="abcdef123456")
    assert not User.objects.filter(username__startswith="smoke.role.abcdef123456.", is_active=True).exists()
    assert not VehicleBrand.objects.filter(name="SMOKE-abcdef123456", is_active=True).exists()
