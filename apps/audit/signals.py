"""ES: Este módulo implementa el componente signals para el dominio de auditoría.

EN: This module implements the signals component for the audit domain.

Contexto existente / Existing context:
Django signal handlers for the audit domain.
"""

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from apps.audit.models import AuditLog
from apps.audit.services import audit_log


@receiver(user_logged_in)
def audit_user_logged_in(sender, request, user, **kwargs):
    audit_log(user=user, action="login.success", target=user, after={"session_started": True})


@receiver(user_logged_out)
def audit_user_logged_out(sender, request, user, **kwargs):
    audit_log(user=user, action="logout", target=user, after={"session_closed": True})


@receiver(user_login_failed)
def audit_user_login_failed(sender, credentials, request, **kwargs):
    login = credentials.get("username") or credentials.get("email") or ""
    audit_log(
        action="login.failed",
        after={"login": login, "reason": "Credenciales inválidas, cuenta bloqueada o usuario inexistente"},
        category=AuditLog.Category.AUTHENTICATION,
        severity=AuditLog.Severity.HIGH,
        result=AuditLog.Result.FAILED,
    )
