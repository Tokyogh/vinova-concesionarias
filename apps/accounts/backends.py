"""ES: Este módulo implementa el componente backends para el dominio de cuentas.

EN: This module implements the backends component for the accounts domain.

Contexto existente / Existing context:
Authentication backend integration for the accounts domain.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.utils import timezone

from apps.security_center.rate_limit import clear_failures, is_blocked, register_failure


class EmailOrUsernameBackend(ModelBackend):
    """Autenticación propia de Vinova Pro por usuario o correo.

    También aplica bloqueo básico por intentos fallidos. No reemplaza medidas de
    producción como rate limiting por IP, pero deja una capa inicial sólida desde
    desarrollo.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """ES: Ejecuta la operación «authenticate» dentro del dominio de cuentas. Además, aplica autorización en backend, registra efectos auditables.

        EN: Executes the «authenticate» operation within the accounts domain. It also enforces server-side authorization, records auditable effects.
        """

        UserModel = get_user_model()
        login = (username or kwargs.get(UserModel.USERNAME_FIELD) or "").strip()
        if not login or password is None:
            return None
        if is_blocked(request, login):
            from apps.audit.models import AuditLog
            from apps.audit.services import audit_log
            audit_log(action="security.login_rate_limited", after={"login": login}, category=AuditLog.Category.AUTHENTICATION, severity=AuditLog.Severity.HIGH, result=AuditLog.Result.DENIED)
            return None

        user = (
            UserModel._default_manager.filter(Q(username__iexact=login) | Q(email__iexact=login))
            .select_related("branch")
            .first()
        )
        if user is None:
            register_failure(request, login)
            return None

        if user.is_locked:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            clear_failures(request, login)
            if user.failed_login_count:
                user.failed_login_count = 0
                user.locked_until = None
                user.save(update_fields=["failed_login_count", "locked_until"])
            return user

        max_attempts = getattr(settings, "VINOVA_LOGIN_MAX_ATTEMPTS", 5)
        lock_minutes = getattr(settings, "VINOVA_LOGIN_LOCK_MINUTES", 15)
        register_failure(request, login)
        user.failed_login_count = min(user.failed_login_count + 1, max_attempts)
        update_fields = ["failed_login_count"]
        if user.failed_login_count >= max_attempts:
            user.locked_until = timezone.now() + timezone.timedelta(minutes=lock_minutes)
            update_fields.append("locked_until")
        user.save(update_fields=update_fields)
        return None
