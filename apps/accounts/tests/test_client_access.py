"""ES: Este módulo especifica regresiones ejecutables para el dominio de cuentas.

EN: This module specifies executable regressions for the accounts domain.

Contexto existente / Existing context:
Regression coverage for client access in the accounts domain.
"""

import hashlib
import re
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import ClientInvitation, PermissionCode, Role, UserRole
from apps.audit.models import AuditLog
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.enterprise.models import CompanyPublicSettings

User = get_user_model()
STRONG_PASSWORD = "VinovaCliente2026!"


@pytest.fixture(autouse=True)
def isolated_public_flows(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    cache.clear()


@pytest.fixture
def client_access_context(db):
    company = Company.objects.create(
        legal_name="Portal Clientes S.A.", commercial_name="Portal Clientes", ruc="1790000000099"
    )
    public_settings = CompanyPublicSettings.objects.create(company=company)
    permission, _ = PermissionCode.objects.update_or_create(
        code="portal.access", defaults={"module": "portal", "name": "Acceso al portal"}
    )
    role, _ = Role.objects.update_or_create(
        code="cliente", defaults={"name": "Cliente", "level": 100, "is_active": True}
    )
    role.permissions.add(permission)
    return public_settings, role


def registration_payload(email="nuevo@example.com"):
    return {
        "first_name": "Ana",
        "last_name": "Cliente",
        "email": email,
        "phone": "0990000000",
        "password1": STRONG_PASSWORD,
        "password2": STRONG_PASSWORD,
        "accept_terms": "on",
        "privacy_acknowledgement": "on",
    }


@pytest.mark.django_db
def test_public_registration_is_disabled_by_default(client, client_access_context):
    response = client.get(reverse("accounts:client_registration"))
    assert response.status_code == 404


@pytest.mark.django_db
def test_registration_creates_new_inactive_customer_account_and_single_use_activation(
    client, client_access_context
):
    public_settings, _ = client_access_context
    public_settings.allow_client_registration = True
    public_settings.save(update_fields=["allow_client_registration"])

    response = client.post(reverse("accounts:client_registration"), registration_payload())

    assert response.status_code == 302
    assert response.url == reverse("accounts:client_registration_done")
    user = User.objects.get(email="nuevo@example.com")
    customer = Customer.objects.get(account=user)
    assert user.is_active is False
    assert customer.source == "registro_web"
    assert not user.has_perm_code("portal.access")
    invitation = ClientInvitation.objects.get(customer=customer)
    assert invitation.kind == ClientInvitation.Kind.REGISTRATION_ACTIVATION
    registration_audit = AuditLog.objects.get(action="accounts.client_registration.create")
    assert registration_audit.after["terms_accepted"] is True
    assert registration_audit.after["privacy_notice_acknowledged"] is True
    assert registration_audit.after["terms_version"].startswith("draft-")
    assert registration_audit.after["privacy_notice_version"].startswith("draft-")
    assert len(mail.outbox) == 1
    activation_path = re.search(r"https?://[^/]+(/accounts/invitacion/[^\s]+)", mail.outbox[0].body).group(1)

    activated = client.post(activation_path, {"confirm": "on"})

    assert activated.status_code == 302
    user.refresh_from_db()
    invitation.refresh_from_db()
    assert user.is_active is True
    assert user.has_perm_code("portal.access")
    assert invitation.status == ClientInvitation.Status.ACCEPTED
    assert client.get(activation_path).status_code == 410


@pytest.mark.django_db
def test_registration_never_auto_links_existing_customer_by_email(client, client_access_context):
    public_settings, _ = client_access_context
    public_settings.allow_client_registration = True
    public_settings.save(update_fields=["allow_client_registration"])
    existing = Customer.objects.create(first_name="Existente", email="existente@example.com")

    response = client.post(
        reverse("accounts:client_registration"), registration_payload("existente@example.com")
    )

    assert response.status_code == 200
    existing.refresh_from_db()
    assert existing.account_id is None
    assert not User.objects.filter(email="existente@example.com").exists()
    assert len(mail.outbox) == 0


@pytest.mark.django_db
@pytest.mark.parametrize("field", ["accept_terms", "privacy_acknowledgement"])
def test_registration_requires_separate_terms_and_privacy_acknowledgement(
    client, client_access_context, field
):
    public_settings, _ = client_access_context
    public_settings.allow_client_registration = True
    public_settings.save(update_fields=["allow_client_registration"])
    payload = registration_payload()
    payload.pop(field)

    response = client.post(reverse("accounts:client_registration"), payload)

    assert response.status_code == 200
    assert field in response.context["form"].errors
    assert not User.objects.filter(email="nuevo@example.com").exists()
    assert not AuditLog.objects.filter(action="accounts.client_registration.create").exists()


@pytest.mark.django_db
def test_staff_invitation_creates_client_account_with_portal_role(client, client_access_context):
    _, _ = client_access_context
    manage = PermissionCode.objects.create(
        module="customers", code="customers.manage", name="Gestionar clientes"
    )
    manager_role = Role.objects.create(code="customer_manager", name="Gestor de clientes")
    manager_role.permissions.add(manage)
    manager = User.objects.create_user(
        username="manager", email="manager@example.com", password="x"
    )
    UserRole.objects.create(user=manager, role=manager_role)
    company = Company.objects.first()
    branch = Branch.objects.create(company=company, name="Matriz", code="INV-01")
    customer = Customer.objects.create(
        first_name="Invitada",
        last_name="Portal",
        email="invitada@example.com",
        assigned_branch=branch,
    )
    client.force_login(manager)

    response = client.post(reverse("customers_internal:invite_account", kwargs={"pk": customer.pk}))

    assert response.status_code == 302
    assert len(mail.outbox) == 1
    invitation_path = re.search(r"https?://[^/]+(/accounts/invitacion/[^\s]+)", mail.outbox[0].body).group(1)
    accepted = client.post(
        invitation_path,
        {"password1": STRONG_PASSWORD, "password2": STRONG_PASSWORD},
    )
    assert accepted.status_code == 302
    customer.refresh_from_db()
    assert customer.account is not None
    assert customer.account.is_active
    assert customer.account.has_perm_code("portal.access")
    assert customer.account.check_password(STRONG_PASSWORD)


@pytest.mark.django_db
def test_expired_invitation_is_rejected(client, client_access_context):
    _, role = client_access_context
    customer = Customer.objects.create(first_name="Caducada", email="caducada@example.com")
    invitation = ClientInvitation.objects.create(
        customer=customer,
        email=customer.email,
        token_digest=hashlib.sha256(b"expired-token").hexdigest(),
        kind=ClientInvitation.Kind.STAFF_INVITATION,
        expires_at=timezone.now() - timedelta(minutes=1),
    )

    response = client.get(reverse("accounts:client_invitation_accept", kwargs={"token": "expired-token"}))

    assert response.status_code == 410
    invitation.refresh_from_db()
    assert invitation.status == ClientInvitation.Status.PENDING


@pytest.mark.django_db
def test_password_reset_is_anti_enumeration_and_token_is_single_use(client, client_access_context):
    user = User.objects.create_user(
        username="reset-client",
        email="reset@example.com",
        password=STRONG_PASSWORD,
        is_active=True,
    )
    known = client.post(reverse("accounts:password_reset"), {"email": user.email})
    unknown = client.post(reverse("accounts:password_reset"), {"email": "missing@example.com"})

    assert known.status_code == unknown.status_code == 302
    assert known.url == unknown.url == reverse("accounts:password_reset_done")
    assert len(mail.outbox) == 1
    reset_path = re.search(r"https?://[^/]+(/accounts/recuperar/[^\s]+)", mail.outbox[0].body).group(1)
    confirm = client.get(reset_path)
    assert confirm.status_code == 302
    set_password_path = confirm.url
    changed = client.post(
        set_password_path,
        {"new_password1": "NuevaVinova2026!", "new_password2": "NuevaVinova2026!"},
    )
    assert changed.status_code == 302
    user.refresh_from_db()
    assert user.check_password("NuevaVinova2026!")
    reused = client.get(reset_path)
    assert reused.status_code == 200
    assert "no es válido" in reused.content.decode()


@pytest.mark.django_db
def test_password_reset_is_rate_limited(client, client_access_context, settings):
    settings.VINOVA_PUBLIC_FORM_MAX_SUBMISSIONS = 1
    url = reverse("accounts:password_reset")

    assert client.post(url, {"email": "first@example.com"}).status_code == 302
    assert client.post(url, {"email": "second@example.com"}).status_code == 429
