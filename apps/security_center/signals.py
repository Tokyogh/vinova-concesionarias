"""ES: Este módulo implementa el componente signals para el dominio de seguridad.

EN: This module implements the signals component for the security center domain.

Contexto existente / Existing context:
Django signal handlers for the security center domain.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_out
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.security_center.models import ActiveSession, UserSecurityProfile


@receiver(post_save, sender=get_user_model())
def ensure_security_profile(sender, instance, created, **kwargs):  # noqa: ARG001
    if created:
        UserSecurityProfile.objects.get_or_create(user=instance)


@receiver(user_logged_out)
def revoke_logged_out_session(sender, request, user, **kwargs):  # noqa: ARG001
    key = getattr(getattr(request, "session", None), "session_key", None)
    if key:
        ActiveSession.objects.filter(session_key=key, revoked_at__isnull=True).update(
            revoked_at=timezone.now(),
            revoke_reason="Cierre de sesión",
        )
