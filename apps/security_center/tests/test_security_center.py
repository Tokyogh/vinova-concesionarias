"""ES: Este módulo especifica regresiones ejecutables para el dominio de seguridad.

EN: This module specifies executable regressions for the security center domain.

Contexto existente / Existing context:
Regression coverage for security center in the security_center domain.
"""

from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
import pytest

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.security_center.models import ActiveSession, SecurityPolicy
from apps.security_center.services import (
    enable_two_factor,
    get_security_profile,
    password_is_expired,
    set_password_securely,
    verify_two_factor,
)
from apps.security_center.totp import code_for, generate_secret

pytestmark = pytest.mark.django_db


def grant(user, *codes):
    role = Role.objects.create(code=f"role-{user.username}", name="Rol", level=50)
    for code in codes:
        perm = PermissionCode.objects.create(module=code.split(".")[0], code=code, name=code)
        role.permissions.add(perm)
    UserRole.objects.create(user=user, role=role)
    return role


def test_totp_and_backup_code_flow(django_user_model):
    user = django_user_model.objects.create_user(username="twofa", email="twofa@example.com", password="Strong!Pass123")
    secret = generate_secret()
    codes = enable_two_factor(user=user, secret=secret, token=code_for(secret))
    profile = get_security_profile(user)
    assert profile.two_factor_enabled is True
    assert profile.encrypted_totp_secret and secret not in profile.encrypted_totp_secret
    assert verify_two_factor(user=user, token=code_for(secret)) is True
    assert verify_two_factor(user=user, token=codes[0]) is True
    profile.refresh_from_db()
    assert len(profile.backup_code_hashes) == len(codes) - 1


def test_password_history_blocks_reuse(django_user_model):
    user = django_user_model.objects.create_user(username="history", email="history@example.com", password="First!Pass123")
    user.last_password_change_at = timezone.now()
    user.save(update_fields=["last_password_change_at"])
    set_password_securely(actor=user, user=user, password="Second!Pass123")
    with pytest.raises(ValidationError):
        validate_password("First!Pass123", user=user)
    validate_password("Third!Pass123", user=user)


def test_security_dashboard_and_headers(client, django_user_model):
    user = django_user_model.objects.create_user(username="security", email="security@example.com", password="Strong!Pass123")
    grant(user, "security.view")
    client.force_login(user)
    response = client.get(reverse("security_center:dashboard"))
    assert response.status_code == 200
    assert "Content-Security-Policy" in response
    assert response["X-Frame-Options"] == "DENY"
    assert ActiveSession.objects.filter(user=user, revoked_at__isnull=True).exists()


def test_enabled_2fa_requires_challenge(client, django_user_model):
    user = django_user_model.objects.create_user(username="challenge", email="challenge@example.com", password="Strong!Pass123")
    secret = generate_secret()
    enable_two_factor(user=user, secret=secret, token=code_for(secret))
    client.force_login(user)
    response = client.get(reverse("accounts:profile"))
    assert response.status_code == 302
    assert reverse("security_center:two_factor_challenge") in response.url
    response = client.post(reverse("security_center:two_factor_challenge"), {"token": code_for(secret)})
    assert response.status_code == 302
    session = client.session
    assert session["vinova_2fa_verified"] is True


def test_two_factor_challenge_is_rate_limited_per_user_and_ip(client, django_user_model):
    cache.clear()
    policy = SecurityPolicy.current()
    policy.login_attempts_per_ip = 2
    policy.login_window_minutes = 15
    policy.save(update_fields=["login_attempts_per_ip", "login_window_minutes", "updated_at"])
    user = django_user_model.objects.create_user(
        username="challenge-limited",
        email="challenge-limited@example.com",
        password="brisa cobre horizonte jazmín",
    )
    secret = generate_secret()
    enable_two_factor(user=user, secret=secret, token=code_for(secret))
    client.force_login(user)

    for _ in range(2):
        response = client.post(reverse("security_center:two_factor_challenge"), {"token": "INVALID-CODE"})
        assert response.status_code == 200
    blocked = client.post(
        reverse("security_center:two_factor_challenge"),
        {"token": code_for(secret)},
    )

    assert blocked.status_code == 429
    assert blocked["Retry-After"] == "900"


def test_valid_two_factor_code_clears_failed_attempt_counter(client, django_user_model):
    cache.clear()
    user = django_user_model.objects.create_user(
        username="challenge-cleared",
        email="challenge-cleared@example.com",
        password="brisa cobre horizonte jazmín",
    )
    secret = generate_secret()
    enable_two_factor(user=user, secret=secret, token=code_for(secret))
    client.force_login(user)
    client.post(reverse("security_center:two_factor_challenge"), {"token": "INVALID-CODE"})

    response = client.post(
        reverse("security_center:two_factor_challenge"),
        {"token": code_for(secret)},
    )

    assert response.status_code == 302


def test_2fa_is_optional_by_default(django_user_model):
    policy = SecurityPolicy.current()
    assert policy.require_2fa_for_superusers is False
    assert policy.require_2fa_for_admin_roles is False


def test_default_password_policy_favors_length_without_composition_or_rotation(django_user_model):
    policy = SecurityPolicy.current()
    assert policy.min_password_length >= 12
    assert policy.require_uppercase is False
    assert policy.require_lowercase is False
    assert policy.require_digit is False
    assert policy.require_symbol is False
    assert policy.password_max_age_days == 0

    validate_password("brisa cobre horizonte jazmín")
    user = django_user_model.objects.create_user(
        username="no-periodic-expiry",
        email="no-periodic-expiry@example.com",
        password="brisa cobre horizonte jazmín",
    )
    user.last_password_change_at = timezone.now() - timezone.timedelta(days=3650)
    assert password_is_expired(user, policy) is False
