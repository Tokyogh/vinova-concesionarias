"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de seguridad.

EN: This module defines persistent models, states, and constraints for the security center domain.

Contexto existente / Existing context:
Persistent domain models and database constraints for the security center domain.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class SecurityPolicy(TimeStampedModel):
    class StaffAccessMode(models.TextChoices):
        OFF = "off", "Desactivado"
        MONITOR = "monitor", "Solo monitoreo"
        ENFORCE = "enforce", "Aplicar restricciones"

    name = models.CharField(max_length=120, default="Política principal")
    is_active = models.BooleanField(default=True, db_index=True)
    min_password_length = models.PositiveSmallIntegerField(default=12)
    require_uppercase = models.BooleanField(default=False)
    require_lowercase = models.BooleanField(default=False)
    require_digit = models.BooleanField(default=False)
    require_symbol = models.BooleanField(default=False)
    password_max_age_days = models.PositiveSmallIntegerField(default=0)
    password_history_count = models.PositiveSmallIntegerField(default=5)
    session_idle_minutes = models.PositiveSmallIntegerField(default=30)
    max_active_sessions = models.PositiveSmallIntegerField(default=3)
    login_attempts_per_ip = models.PositiveSmallIntegerField(default=10)
    login_window_minutes = models.PositiveSmallIntegerField(default=15)
    require_2fa_for_superusers = models.BooleanField(default=False)
    require_2fa_for_admin_roles = models.BooleanField(default=False)
    admin_role_level_threshold = models.PositiveSmallIntegerField(default=10)
    staff_access_mode = models.CharField(
        max_length=20,
        choices=StaffAccessMode.choices,
        default=StaffAccessMode.OFF,
    )
    trusted_staff_networks = models.TextField(
        blank=True,
        help_text="IP/CIDR corporativas o de VPN, una por línea.",
    )
    staff_access_approval_minutes = models.PositiveSmallIntegerField(default=60)
    staff_access_request_minutes = models.PositiveSmallIntegerField(default=15)

    class Meta:
        verbose_name = "Política de seguridad"
        verbose_name_plural = "Políticas de seguridad"
        ordering = ["-is_active", "name"]

    def __str__(self):
        return self.name

    @classmethod
    def current(cls):
        policy = cls.objects.filter(is_active=True).order_by("pk").first()
        if policy:
            return policy
        return cls.objects.create()


class UserSecurityProfile(TimeStampedModel):
    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="security_profile")
    two_factor_enabled = models.BooleanField(default=False, db_index=True)
    encrypted_totp_secret = models.TextField(blank=True)
    backup_code_hashes = models.JSONField(default=list, blank=True)
    two_factor_confirmed_at = models.DateTimeField(null=True, blank=True)
    last_two_factor_at = models.DateTimeField(null=True, blank=True)
    backup_codes_generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Perfil de seguridad"
        verbose_name_plural = "Perfiles de seguridad"

    def __str__(self):
        return f"Seguridad de {self.user}"

    def is_two_factor_required(self, policy=None):
        policy = policy or SecurityPolicy.current()
        if self.user.is_superuser and policy.require_2fa_for_superusers:
            return True
        if policy.require_2fa_for_admin_roles:
            return self.user.user_roles.filter(
                is_active=True,
                role__is_active=True,
                role__level__lte=policy.admin_role_level_threshold,
            ).exists()
        return False


class PasswordHistory(TimeStampedModel):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="password_history")
    encoded_password = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Historial de contraseña"
        verbose_name_plural = "Historial de contraseñas"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]


class ActiveSession(TimeStampedModel):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="tracked_sessions")
    session_key = models.CharField(max_length=64, unique=True, db_index=True)
    ip_hash = models.CharField(max_length=64, blank=True, db_index=True)
    user_agent = models.CharField(max_length=500, blank=True)
    last_seen_at = models.DateTimeField(default=timezone.now, db_index=True)
    two_factor_verified_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True, db_index=True)
    revoke_reason = models.CharField(max_length=180, blank=True)

    class Meta:
        verbose_name = "Sesión activa"
        verbose_name_plural = "Sesiones activas"
        ordering = ["-last_seen_at"]
        indexes = [models.Index(fields=["user", "revoked_at", "-last_seen_at"])]

    @property
    def is_active(self):
        return self.revoked_at is None


class StaffAccessRequest(TimeStampedModel):
    """Solicitud temporal ligada a una sesión, IP y señal de dispositivo.

    Temporary request bound to one session, IP address, and device signal.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        APPROVED = "approved", "Aprobada"
        REJECTED = "rejected", "Rechazada"
        REVOKED = "revoked", "Revocada"
        EXPIRED = "expired", "Expirada"
        CANCELLED = "cancelled", "Cancelada"

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="staff_access_requests",
    )
    session_reference = models.CharField(max_length=64, db_index=True)
    ip_hash = models.CharField(max_length=64, db_index=True)
    user_agent_hash = models.CharField(max_length=64, db_index=True)
    risk_reasons = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    request_expires_at = models.DateTimeField(db_index=True)
    access_expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    decided_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="staff_access_decisions",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status", "-created_at"]),
            models.Index(fields=["session_reference", "ip_hash", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "session_reference", "ip_hash", "user_agent_hash"],
                condition=models.Q(status="pending"),
                name="unique_pending_staff_access_context",
            )
        ]
        verbose_name = "Solicitud de acceso Staff"
        verbose_name_plural = "Solicitudes de acceso Staff"

    @property
    def is_active_approval(self):
        return bool(
            self.status == self.Status.APPROVED
            and self.access_expires_at
            and self.access_expires_at > timezone.now()
        )
