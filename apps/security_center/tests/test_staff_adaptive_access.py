"""ES: Este módulo especifica regresiones ejecutables para el dominio de seguridad.

EN: This module specifies executable regressions for the security center domain.

Contexto existente / Existing context:
Regresiones de acceso Staff adaptativo, aprobación y recuperación.

Adaptive Staff access, approval, and recovery regressions.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management.base import CommandError
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.audit.models import AuditLog
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.notifications.models import NotificationMessage
from apps.security_center.models import SecurityPolicy, StaffAccessRequest
from apps.security_center.forms import SecurityPolicyForm
from apps.security_center.services import get_security_profile
from apps.security_center.staff_access import (
    decide_staff_access,
    revoke_staff_access,
    validate_staff_enforcement_readiness,
)

pytestmark = pytest.mark.django_db


def _permission(code):
    return PermissionCode.objects.get_or_create(
        code=code,
        defaults={"module": code.split(".")[0], "name": code},
    )[0]


def _staff_user(django_user_model, username, *, level, permissions, branch=None):
    user = django_user_model.objects.create_user(
        username=username,
        email=f"{username}@example.invalid",
        password="brisa cobre horizonte jazmín",
    )
    role = Role.objects.create(code=f"role-{username}", name=username, level=level)
    role.permissions.set([_permission(code) for code in permissions])
    UserRole.objects.create(user=user, role=role, branch=branch)
    return user


def _verified_client(client, user):
    client.force_login(user)
    profile = get_security_profile(user)
    profile.two_factor_enabled = True
    profile.save(update_fields=["two_factor_enabled", "updated_at"])
    session = client.session
    session["vinova_2fa_verified"] = True
    session.save()
    return client


@pytest.fixture(name="access_context")
def access_context_fixture(django_user_model, client):
    requester = _staff_user(
        django_user_model,
        "risk-requester",
        level=20,
        permissions=("dashboard.view",),
    )
    approver = _staff_user(
        django_user_model,
        "risk-approver",
        level=5,
        permissions=("dashboard.view", "security.view", "security.approve_staff_access"),
    )
    policy = SecurityPolicy.current()
    policy.staff_access_mode = SecurityPolicy.StaffAccessMode.ENFORCE
    policy.trusted_staff_networks = "10.0.0.0/8"
    policy.staff_access_approval_minutes = 30
    policy.staff_access_request_minutes = 15
    policy.save()
    _verified_client(client, requester)
    return {"requester": requester, "approver": approver, "policy": policy, "client": client}


def _create_request(context):
    response = context["client"].get(
        reverse("dashboard:staff_home"),
        REMOTE_ADDR="198.51.100.20",
        HTTP_USER_AGENT="Vinova QA Browser",
    )
    assert response.status_code == 302
    assert response.url == reverse("security_center:staff_access_pending")
    return StaffAccessRequest.objects.get(user=context["requester"], status=StaffAccessRequest.Status.PENDING)


def test_enforcement_creates_one_idempotent_pending_request(access_context):
    first = _create_request(access_context)
    second_response = access_context["client"].get(
        reverse("dashboard:staff_home"),
        REMOTE_ADDR="198.51.100.20",
        HTTP_USER_AGENT="Vinova QA Browser",
    )

    assert second_response.status_code == 302
    assert StaffAccessRequest.objects.filter(user=access_context["requester"]).count() == 1
    assert first.risk_reasons == ["untrusted_network"]


def test_request_sends_minimal_in_app_notice_to_approver(
    access_context,
    django_capture_on_commit_callbacks,
):
    with django_capture_on_commit_callbacks(execute=True):
        access_request = _create_request(access_context)

    message = NotificationMessage.objects.get(dedup_key=f"staff-access-request:{access_request.pk}")
    assert message.recipients.filter(user=access_context["approver"]).exists()
    assert "198.51.100.20" not in message.body
    assert access_request.ip_hash not in message.body


def test_trusted_network_allows_staff_without_exception(access_context):
    response = access_context["client"].get(
        reverse("dashboard:staff_home"),
        REMOTE_ADDR="10.20.30.40",
        HTTP_USER_AGENT="Vinova QA Browser",
    )

    assert response.status_code == 200
    assert not StaffAccessRequest.objects.filter(user=access_context["requester"]).exists()


def test_outside_policy_requires_two_factor_before_request(access_context):
    profile = get_security_profile(access_context["requester"])
    profile.two_factor_enabled = False
    profile.save(update_fields=["two_factor_enabled", "updated_at"])
    session = access_context["client"].session
    session.pop("vinova_2fa_verified", None)
    session.save()

    response = access_context["client"].get(
        reverse("dashboard:staff_home"),
        REMOTE_ADDR="198.51.100.20",
    )

    assert response.status_code == 302
    assert response.url == reverse("security_center:two_factor_setup")
    assert not StaffAccessRequest.objects.filter(user=access_context["requester"]).exists()


def test_higher_rank_approver_grants_only_the_bound_context(access_context):
    access_request = _create_request(access_context)
    from django.test import Client

    approver_client = _verified_client(Client(), access_context["approver"])
    approved = approver_client.post(
        reverse("security_center:staff_access_approve", args=[access_request.pk]),
        {"note": "Excepción operativa verificada"},
        REMOTE_ADDR="10.1.2.3",
        HTTP_USER_AGENT="Approver Browser",
    )
    assert approved.status_code == 302
    access_request.refresh_from_db()
    assert access_request.status == StaffAccessRequest.Status.APPROVED
    assert access_request.decided_by == access_context["approver"]

    allowed = access_context["client"].get(
        reverse("dashboard:staff_home"),
        REMOTE_ADDR="198.51.100.20",
        HTTP_USER_AGENT="Vinova QA Browser",
    )
    changed_device = access_context["client"].get(
        reverse("dashboard:staff_home"),
        REMOTE_ADDR="198.51.100.20",
        HTTP_USER_AGENT="Different Browser",
    )

    assert allowed.status_code == 200
    assert changed_device.status_code == 302
    assert StaffAccessRequest.objects.filter(user=access_context["requester"]).count() == 2


def test_pending_access_blocks_privileged_api_with_json(access_context):
    _create_request(access_context)

    response = access_context["client"].get(
        "/api/v1/meta/",
        REMOTE_ADDR="198.51.100.20",
        HTTP_USER_AGENT="Vinova QA Browser",
        HTTP_ACCEPT="application/json",
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Acceso Staff pendiente de aprobación."


def test_self_approval_and_same_rank_approval_are_denied(access_context, django_user_model):
    access_request = _create_request(access_context)
    with pytest.raises(PermissionDenied, match="propia"):
        decide_staff_access(
            access_request_id=access_request.pk,
            actor=access_context["requester"],
            approve=True,
            note="",
            actor_2fa_verified=True,
        )
    peer = _staff_user(
        django_user_model,
        "risk-peer",
        level=20,
        permissions=("security.approve_staff_access",),
    )
    with pytest.raises(PermissionDenied, match="rango superior"):
        decide_staff_access(
            access_request_id=access_request.pk,
            actor=peer,
            approve=True,
            note="",
            actor_2fa_verified=True,
        )


def test_decision_is_single_use_and_approval_expires(access_context):
    access_request = _create_request(access_context)
    decide_staff_access(
        access_request_id=access_request.pk,
        actor=access_context["approver"],
        approve=True,
        note="",
        actor_2fa_verified=True,
    )
    with pytest.raises(ValidationError, match="resuelta"):
        decide_staff_access(
            access_request_id=access_request.pk,
            actor=access_context["approver"],
            approve=True,
            note="",
            actor_2fa_verified=True,
        )
    StaffAccessRequest.objects.filter(pk=access_request.pk).update(
        access_expires_at=timezone.now() - timedelta(minutes=1)
    )

    response = access_context["client"].get(
        reverse("dashboard:staff_home"),
        REMOTE_ADDR="198.51.100.20",
        HTTP_USER_AGENT="Vinova QA Browser",
    )

    assert response.status_code == 302
    access_request.refresh_from_db()
    assert access_request.status == StaffAccessRequest.Status.EXPIRED


def test_approval_can_be_revoked_and_is_revalidated(access_context):
    access_request = _create_request(access_context)
    decide_staff_access(
        access_request_id=access_request.pk,
        actor=access_context["approver"],
        approve=True,
        note="",
        actor_2fa_verified=True,
    )
    revoke_staff_access(
        access_request_id=access_request.pk,
        actor=access_context["approver"],
        actor_2fa_verified=True,
    )

    response = access_context["client"].get(
        reverse("dashboard:staff_home"),
        REMOTE_ADDR="198.51.100.20",
        HTTP_USER_AGENT="Vinova QA Browser",
    )

    access_request.refresh_from_db()
    assert access_request.status == StaffAccessRequest.Status.REVOKED
    assert response.status_code == 302
    assert StaffAccessRequest.objects.filter(
        user=access_context["requester"], status=StaffAccessRequest.Status.PENDING
    ).exists()


def test_decision_requires_2fa_and_global_permission(access_context, django_user_model):
    access_request = _create_request(access_context)
    with pytest.raises(PermissionDenied, match="2FA"):
        decide_staff_access(
            access_request_id=access_request.pk,
            actor=access_context["approver"],
            approve=True,
            note="",
            actor_2fa_verified=False,
        )
    company = Company.objects.create(
        legal_name="Compañía de prueba",
        commercial_name="Prueba",
        ruc="1799999999003",
    )
    branch = Branch.objects.create(company=company, name="Sucursal", code="SEC", city="Quito")
    scoped = _staff_user(
        django_user_model,
        "scoped-approver",
        level=1,
        permissions=("security.approve_staff_access",),
        branch=branch,
    )
    with pytest.raises(PermissionDenied, match="global"):
        decide_staff_access(
            access_request_id=access_request.pk,
            actor=scoped,
            approve=True,
            note="",
            actor_2fa_verified=True,
        )


def test_monitor_mode_audits_once_without_blocking(access_context):
    policy = access_context["policy"]
    policy.staff_access_mode = SecurityPolicy.StaffAccessMode.MONITOR
    policy.save(update_fields=["staff_access_mode", "updated_at"])

    for _ in range(2):
        response = access_context["client"].get(
            reverse("dashboard:staff_home"),
            REMOTE_ADDR="198.51.100.20",
            HTTP_USER_AGENT="Vinova QA Browser",
        )
        assert response.status_code == 200

    assert AuditLog.objects.filter(
        user=access_context["requester"], action="security.staff_access.monitored"
    ).count() == 1


def test_customers_are_not_subject_to_staff_network_policy(access_context, django_user_model):
    customer = django_user_model.objects.create_user(
        username="portal-only",
        email="portal-only@example.invalid",
        password="brisa cobre horizonte jazmín",
    )
    from django.test import Client

    portal_client = Client()
    portal_client.force_login(customer)
    response = portal_client.get(reverse("accounts:profile"), REMOTE_ADDR="198.51.100.30")

    assert response.status_code == 200
    assert not StaffAccessRequest.objects.filter(user=customer).exists()


def test_enforcement_readiness_requires_network_and_independent_2fa_approver(
    access_context,
):
    policy = access_context["policy"]
    policy.trusted_staff_networks = ""
    with pytest.raises(ValidationError, match="red corporativa"):
        validate_staff_enforcement_readiness(actor=access_context["requester"], policy=policy)


def test_policy_form_bounds_temporary_windows(access_context):
    policy = access_context["policy"]
    data = {field: getattr(policy, field) for field in SecurityPolicyForm.Meta.fields}
    data["staff_access_approval_minutes"] = 1441
    data["staff_access_request_minutes"] = 61

    form = SecurityPolicyForm(data=data, instance=policy)

    assert not form.is_valid()
    assert "staff_access_approval_minutes" in form.errors
    assert "staff_access_request_minutes" in form.errors
    policy.trusted_staff_networks = "10.0.0.0/8"
    profile = get_security_profile(access_context["approver"])
    profile.two_factor_enabled = False
    profile.save(update_fields=["two_factor_enabled", "updated_at"])
    with pytest.raises(ValidationError, match="otro aprobador"):
        validate_staff_enforcement_readiness(actor=access_context["requester"], policy=policy)


def test_emergency_recovery_requires_literal_confirmation(access_context):
    with pytest.raises(CommandError, match="DISABLE-STAFF-ACCESS"):
        call_command("disable_staff_access_policy")

    call_command("disable_staff_access_policy", confirm="DISABLE-STAFF-ACCESS", verbosity=0)
    access_context["policy"].refresh_from_db()
    assert access_context["policy"].staff_access_mode == SecurityPolicy.StaffAccessMode.OFF
