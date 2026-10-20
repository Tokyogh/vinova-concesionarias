"""ES: Este módulo especifica regresiones ejecutables para el dominio de seguridad.

EN: This module specifies executable regressions for the security center domain.

Contexto existente / Existing context:
Regresiones de cookies y ciclo de sesiones para F7.

Cookie and session lifecycle regressions for F7.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.security_center.models import ActiveSession, PasswordHistory, SecurityPolicy

pytestmark = pytest.mark.django_db


def _user(django_user_model, username="session-user"):
    return django_user_model.objects.create_user(
        username=username,
        email=f"{username}@example.invalid",
        password="brisa cobre horizonte jazmín",
    )


def _track(client, user):
    client.force_login(user)
    response = client.get(reverse("accounts:profile"))
    assert response.status_code == 200
    return client.session.session_key


def test_login_rotates_an_anonymous_session_key(client, django_user_model):
    user = _user(django_user_model, "rotation-user")
    anonymous = client.session
    anonymous["pre_login_marker"] = "present"
    anonymous.save()
    previous_key = anonymous.session_key

    response = client.post(
        reverse("accounts:login"),
        {"username": user.username, "password": "brisa cobre horizonte jazmín"},
    )

    assert response.status_code == 302
    assert client.session.session_key != previous_key


def test_password_change_rotates_current_and_revokes_other_sessions(client, django_user_model):
    user = _user(django_user_model, "password-change-user")
    current_key = _track(client, user)
    from django.test import Client

    other_client = Client()
    other_key = _track(other_client, user)

    response = client.post(
        reverse("security_center:password_change"),
        {
            "old_password": "brisa cobre horizonte jazmín",
            "new_password1": "océano violeta sendero tranquilo",
            "new_password2": "océano violeta sendero tranquilo",
        },
    )

    assert response.status_code == 302
    user.refresh_from_db()
    assert user.check_password("océano violeta sendero tranquilo")
    assert client.session.session_key not in {current_key, other_key}
    assert ActiveSession.objects.filter(session_key=current_key, revoked_at__isnull=False).exists()
    assert ActiveSession.objects.filter(session_key=other_key, revoked_at__isnull=False).exists()
    assert ActiveSession.objects.filter(session_key=client.session.session_key, revoked_at__isnull=True).exists()
    assert other_client.get(reverse("accounts:profile")).status_code == 302


def test_password_reset_uses_history_and_revokes_existing_sessions(client, django_user_model):
    user = _user(django_user_model, "password-reset-user")
    tracked_key = _track(client, user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    from django.test import Client

    reset_client = Client()
    response = reset_client.get(
        reverse("accounts:password_reset_confirm", kwargs={"uidb64": uid, "token": token})
    )
    assert response.status_code == 302
    response = reset_client.post(
        response.url,
        {
            "new_password1": "bosque ámbar camino sereno",
            "new_password2": "bosque ámbar camino sereno",
        },
    )

    assert response.status_code == 302
    user.refresh_from_db()
    assert user.check_password("bosque ámbar camino sereno")
    assert user.last_password_change_at is not None
    assert PasswordHistory.objects.filter(user=user).exists()
    assert ActiveSession.objects.filter(session_key=tracked_key, revoked_at__isnull=False).exists()
    assert client.get(reverse("accounts:profile")).status_code == 302


def test_idle_timeout_invalidates_and_marks_the_tracked_session(client, django_user_model):
    user = _user(django_user_model, "idle-user")
    tracked_key = _track(client, user)
    policy = SecurityPolicy.current()
    session = client.session
    session["vinova_last_activity"] = (
        timezone.now() - timedelta(minutes=policy.session_idle_minutes + 1)
    ).isoformat()
    session.save()

    response = client.get(reverse("accounts:profile"))

    assert response.status_code == 302
    assert response.url == reverse("accounts:login")
    assert not client.session.session_key
    assert ActiveSession.objects.filter(session_key=tracked_key, revoked_at__isnull=False).exists()


def test_absolute_timeout_invalidates_an_active_session(client, django_user_model, settings):
    settings.VINOVA_SESSION_ABSOLUTE_MINUTES = 60
    user = _user(django_user_model, "absolute-timeout-user")
    tracked_key = _track(client, user)
    ActiveSession.objects.filter(session_key=tracked_key).update(created_at=timezone.now() - timedelta(minutes=61))

    response = client.get(reverse("accounts:profile"))

    assert response.status_code == 302
    assert response.url == reverse("accounts:login")
    assert not client.session.session_key
    assert ActiveSession.objects.filter(session_key=tracked_key, revoked_at__isnull=False).exists()


def test_htmx_disables_eval_scripts_and_browser_history_cache(client):
    response = client.get(reverse("dashboard:home"))
    body = response.content.decode()

    assert '"allowEval":false' in body
    assert '"allowScriptTags":false' in body
    assert '"historyCacheSize":0' in body
    assert response.wsgi_request.csp_nonce in body
