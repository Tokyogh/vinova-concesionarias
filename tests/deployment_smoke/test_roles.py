"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for roles in the deployment_smoke domain.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from tests.deployment_smoke.helpers.browser import BrowserSession
from tests.deployment_smoke.helpers.runtime import run_check
from tests.deployment_smoke.role_contract import EXPECTED_DASHBOARD_PATH, PROBES, ROLE_CODES, expected_allowed

__test__ = False


def run(state, session=None):  # noqa: ANN001
    manifest = _load_manifest(state.config.role_credentials_file)
    matrix: dict[str, dict] = {}
    for role_code in ROLE_CODES:
        account = manifest["accounts"].get(role_code)
        result = run_check(
            state,
            code=f"roles.{role_code}",
            scenario="roles",
            title=f"Matriz completa: {role_code}",
            callback=lambda role_code=role_code, account=account: _role_case(
                state, role_code, account, session
            ),
        )
        matrix[role_code] = result.details
    inactive = manifest["accounts"].get("inactive")
    result = run_check(
        state,
        code="roles.inactive",
        scenario="roles",
        title="Usuario inactivo bloqueado",
        callback=lambda: _inactive_case(state, inactive, session),
    )
    matrix["inactive"] = result.details
    state.metadata["role_matrix"] = matrix
    state.metadata["role_matrix_summary"] = {
        "roles_evaluated": len(ROLE_CODES),
        "probes_per_role": len(PROBES),
        "expected_contract_cells": len(ROLE_CODES) * len(PROBES),
        "manifest_run_id": manifest["run_id"],
    }


def _load_manifest(path: Path | None) -> dict:
    if path is None:
        raise AssertionError("El escenario roles requiere --role-credentials-file.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise AssertionError("Versión de manifest de roles no soportada.")
    accounts = payload.get("accounts")
    if not isinstance(accounts, dict):
        raise AssertionError("El manifest no contiene accounts.")
    missing = sorted((set(ROLE_CODES) | {"inactive"}) - set(accounts))
    if missing:
        raise AssertionError(f"Faltan cuentas en el manifest: {', '.join(missing)}.")
    expires_at = payload.get("expires_at")
    if expires_at:
        parsed = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if parsed.astimezone(UTC) <= datetime.now(UTC):
            raise AssertionError("El manifest de roles expiró.")
    return payload


def _role_case(state, role_code: str, account: dict | None, parent_session=None) -> dict:  # noqa: ANN001
    if not account or not account.get("username") or not account.get("password"):
        raise AssertionError(f"Credenciales incompletas para {role_code}.")
    output = state.output_dir / "role-evidence" / role_code
    cells = []
    discrepancies = []
    with BrowserSession(
        base_url=state.config.base_url,
        browser_name=state.config.browser,
        timeout_seconds=state.config.timeout_seconds,
        headless=state.config.headless,
        output_dir=output,
        record_video=False,
        verify_tls=state.config.verify_tls,
        shared_browser=parent_session.browser if parent_session is not None else None,
    ) as role_session:
        role_session.login(account["username"], account["password"])
        dashboard = role_session.goto("/dashboard/")
        expected_dashboard = EXPECTED_DASHBOARD_PATH[role_code]
        if role_code == "cliente":
            dashboard_ok = expected_dashboard in dashboard.url
        else:
            dashboard_ok = dashboard.locator(f"a[href='{expected_dashboard}']").count() > 0
        if not dashboard_ok:
            discrepancies.append(
                {
                    "probe": "dashboard.profile",
                    "expected": expected_dashboard,
                    "actual": dashboard.url,
                }
            )
        evidence = role_session.screenshot(f"dashboard-{role_code}")

        assert role_session.page is not None
        for probe in PROBES:
            expected = expected_allowed(role_code, probe.permissions)
            response = role_session.page.request.get(role_session.url(probe.path), max_redirects=0)
            status = response.status
            location = response.headers.get("location", "")
            allowed_actual = _is_allowed_response(status, location)
            matches = expected == allowed_actual
            cell = {
                "probe": probe.code,
                "label": probe.label,
                "path": probe.path,
                "capability": probe.capability,
                "expected": "PERMITIDO" if expected else "BLOQUEADO",
                "actual": "PERMITIDO" if allowed_actual else "BLOQUEADO",
                "status_code": status,
                "location": location,
                "matches": matches,
            }
            cells.append(cell)
            if not matches:
                discrepancies.append(cell)

        role_session.logout()

    result = {
        "role": role_code,
        "branch_code": account.get("branch_code"),
        "dashboard_expected": expected_dashboard,
        "dashboard_ok": dashboard_ok,
        "passed_cells": sum(cell["matches"] for cell in cells),
        "failed_cells": len(discrepancies),
        "cells": cells,
        "evidence": [str((output / evidence).relative_to(state.output_dir))],
    }
    if discrepancies:
        preview = ", ".join(item["probe"] for item in discrepancies[:6])
        result.update(
            {
                "status": "failed",
                "message": (
                    f"{role_code} presenta {len(discrepancies)} discrepancias de autorización: {preview}."
                ),
            }
        )
    return result


def _inactive_case(state, account: dict | None, parent_session=None) -> dict:  # noqa: ANN001
    if not account:
        raise AssertionError("Falta la cuenta inactive en el manifest.")
    output = state.output_dir / "role-evidence" / "inactive"
    with BrowserSession(
        base_url=state.config.base_url,
        browser_name=state.config.browser,
        timeout_seconds=state.config.timeout_seconds,
        headless=state.config.headless,
        output_dir=output,
        record_video=False,
        verify_tls=state.config.verify_tls,
        shared_browser=parent_session.browser if parent_session is not None else None,
    ) as role_session:
        try:
            role_session.login(account["username"], account["password"])
        except AssertionError:
            return {"login_blocked": True}
    raise AssertionError("El usuario inactivo logró iniciar sesión.")


def _is_allowed_response(status: int, location: str) -> bool:
    blocked_redirect = any(path in location for path in ("/accounts/login/", "/accounts/profile/"))
    if blocked_redirect or status in {401, 403}:
        return False
    return 200 <= status < 400
