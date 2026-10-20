"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de seguridad.

EN: This module implements business services and transactional effects for the security center domain.

Contexto existente / Existing context:
Transactional business services for the security center domain.
"""

from __future__ import annotations

import hashlib
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.sessions.models import Session
from django.db import transaction
from django.utils import timezone

from apps.audit.services import audit_log
from apps.security_center.crypto import decrypt_secret, encrypt_secret
from apps.security_center.models import ActiveSession, PasswordHistory, SecurityPolicy, UserSecurityProfile
from apps.security_center.totp import verify_code

User = get_user_model()


def get_security_profile(user) -> UserSecurityProfile:
    profile, _ = UserSecurityProfile.objects.get_or_create(user=user)
    return profile


def hash_ip(ip: str) -> str:
    return hashlib.sha256(f"{settings.SECRET_KEY}:{ip}".encode("utf-8")).hexdigest() if ip else ""


def generate_backup_codes(count: int = 8) -> list[str]:
    return [f"{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}" for _ in range(count)]


@transaction.atomic
def enable_two_factor(*, user, secret: str, token: str) -> list[str]:
    if not verify_code(secret, token):
        raise ValueError("El código temporal no es válido.")
    codes = generate_backup_codes()
    profile = get_security_profile(user)
    profile.encrypted_totp_secret = encrypt_secret(secret)
    profile.two_factor_enabled = True
    profile.two_factor_confirmed_at = timezone.now()
    profile.last_two_factor_at = timezone.now()
    profile.backup_code_hashes = [make_password(code) for code in codes]
    profile.backup_codes_generated_at = timezone.now()
    profile.save()
    audit_log(user=user, action="security.2fa.enabled", target=user, after={"enabled": True, "backup_codes": len(codes)})
    return codes


def verify_two_factor(*, user, token: str) -> bool:
    profile = get_security_profile(user)
    normalized = token.strip().upper()
    secret = decrypt_secret(profile.encrypted_totp_secret)
    if secret and verify_code(secret, normalized):
        profile.last_two_factor_at = timezone.now()
        profile.save(update_fields=["last_two_factor_at", "updated_at"])
        return True
    hashes = list(profile.backup_code_hashes or [])
    for index, encoded in enumerate(hashes):
        if check_password(normalized, encoded):
            hashes.pop(index)
            profile.backup_code_hashes = hashes
            profile.last_two_factor_at = timezone.now()
            profile.save(update_fields=["backup_code_hashes", "last_two_factor_at", "updated_at"])
            audit_log(user=user, action="security.2fa.backup_code_used", target=user, after={"remaining": len(hashes)})
            return True
    return False


@transaction.atomic
def disable_two_factor(*, actor, user, reason: str = ""):
    profile = get_security_profile(user)
    before = {"enabled": profile.two_factor_enabled}
    profile.two_factor_enabled = False
    profile.encrypted_totp_secret = ""
    profile.backup_code_hashes = []
    profile.two_factor_confirmed_at = None
    profile.save()
    audit_log(user=actor, action="security.2fa.disabled", target=user, before=before, after={"enabled": False, "reason": reason})


@transaction.atomic
def set_password_securely(*, actor, user, password: str, must_change_password: bool = False, action="security.password.changed"):
    if user.password:
        PasswordHistory.objects.create(user=user, encoded_password=user.password)
    user.set_password(password)
    user.must_change_password = must_change_password
    user.failed_login_count = 0
    user.locked_until = None
    user.last_password_change_at = timezone.now()
    user.save(update_fields=["password", "must_change_password", "failed_login_count", "locked_until", "last_password_change_at"])
    policy = SecurityPolicy.current()
    stale_ids = list(PasswordHistory.objects.filter(user=user).order_by("-created_at").values_list("id", flat=True)[policy.password_history_count :])
    if stale_ids:
        PasswordHistory.objects.filter(id__in=stale_ids).delete()
    audit_log(user=actor, action=action, target=user, after={"must_change_password": must_change_password})
    return user


def register_session(*, request, user) -> ActiveSession:
    """ES: Ejecuta la operación «register session» dentro del dominio de seguridad.

    EN: Executes the «register session» operation within the security center domain.
    """

    if not request.session.session_key:
        request.session.save()
    session_key = request.session.session_key
    now = timezone.now()
    current_ip_hash = hash_ip(getattr(request, "audit_ip", "") or request.META.get("REMOTE_ADDR", ""))
    current_agent = request.META.get("HTTP_USER_AGENT", "")[:500]
    session, created = ActiveSession.objects.get_or_create(
        session_key=session_key,
        defaults={
            "user": user,
            "ip_hash": current_ip_hash,
            "user_agent": current_agent,
            "last_seen_at": now,
        },
    )
    if not created and session.revoked_at is None:
        update_fields = []
        if session.user_id != user.pk:
            session.user = user
            update_fields.append("user")
        if session.last_seen_at <= now - timezone.timedelta(seconds=60):
            session.last_seen_at = now
            update_fields.append("last_seen_at")
        if session.ip_hash != current_ip_hash:
            session.ip_hash = current_ip_hash
            update_fields.append("ip_hash")
        if session.user_agent != current_agent:
            session.user_agent = current_agent
            update_fields.append("user_agent")
        if update_fields:
            update_fields.append("updated_at")
            session.save(update_fields=update_fields)
    if created:
        policy = SecurityPolicy.current()
        active = list(ActiveSession.objects.filter(user=user, revoked_at__isnull=True).order_by("-last_seen_at"))
        for old in active[policy.max_active_sessions :]:
            revoke_session(old, actor=user, reason="Límite de sesiones activas")
    return session


def revoke_session(session: ActiveSession, *, actor=None, reason="Revocada"):
    if session.revoked_at:
        return session
    session.revoked_at = timezone.now()
    session.revoke_reason = reason[:180]
    session.save(update_fields=["revoked_at", "revoke_reason", "updated_at"])
    Session.objects.filter(session_key=session.session_key).delete()
    audit_log(user=actor, action="security.session.revoked", target=session, after={"user_id": session.user_id, "reason": reason})
    return session


def revoke_user_sessions(*, user, actor=None, keep_session_key: str | None = None, reason="Revocadas") -> int:
    """ES: Revoca sesiones rastreadas de una cuenta. EN: Revokes an account's tracked sessions."""

    sessions = ActiveSession.objects.filter(user=user, revoked_at__isnull=True)
    if keep_session_key:
        sessions = sessions.exclude(session_key=keep_session_key)
    revoked = 0
    for session in sessions:
        revoke_session(session, actor=actor, reason=reason)
        revoked += 1
    return revoked


def password_is_expired(user, policy=None) -> bool:
    policy = policy or SecurityPolicy.current()
    if not policy.password_max_age_days or not user.last_password_change_at:
        return False
    return user.last_password_change_at <= timezone.now() - timezone.timedelta(days=policy.password_max_age_days)
