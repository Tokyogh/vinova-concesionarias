"""ES: Este módulo implementa el componente staff access para el dominio de seguridad.

EN: This module implements the staff access component for the security center domain.

Contexto existente / Existing context:
Acceso Staff adaptativo basado en red, sesión, dispositivo y aprobación temporal.

Adaptive Staff access based on network, session, device, and temporary approval.
"""

from __future__ import annotations

import hashlib
import ipaddress
import logging
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Min, Q
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.audit.services import audit_log
from apps.security_center.models import SecurityPolicy, StaffAccessRequest
from apps.security_center.rate_limit import client_ip

logger = logging.getLogger(__name__)

SAFE_EXACT_PATHS = {
    "/",
    "/accounts/login/",
    "/accounts/logout/",
    "/accounts/profile/",
    "/nosotros/",
    "/security/staff-access/",
    "/security/staff-access/cancel/",
    "/servicios/",
}
SAFE_PREFIXES = (
    "/static/",
    "/media/",
    "/health/",
    "/vehiculos/",
    "/vehicles/",
    "/instituciones/",
    "/repuestos/",
    "/leads/request/",
    "/privacy/request/",
    "/security/2fa/",
    "/security/password/change/",
)


@dataclass(frozen=True)
class StaffAccessAssessment:
    allowed: bool
    monitored: bool = False
    risk_reasons: tuple[str, ...] = ()
    session_reference: str = ""
    ip_hash: str = ""
    user_agent_hash: str = ""
    approval: StaffAccessRequest | None = None


def _reference(value: str) -> str:
    return hashlib.sha256(f"{settings.SECRET_KEY}:{value}".encode("utf-8")).hexdigest()


def parse_trusted_staff_networks(value: str) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    """ES: Normaliza redes configuradas. EN: Normalizes configured trusted networks."""

    entries = [item.strip() for item in (value or "").replace(",", "\n").splitlines() if item.strip()]
    if len(entries) > 100:
        raise ValidationError("Configura como máximo 100 redes Staff.")
    networks = []
    for entry in entries:
        try:
            network = ipaddress.ip_network(entry, strict=False)
        except ValueError as exc:
            raise ValidationError(f"IP o CIDR Staff inválido: {entry}") from exc
        if network.prefixlen == 0:
            raise ValidationError("No se permite confiar en todo Internet mediante una red /0.")
        networks.append(network)
    return tuple(networks)


def staff_access_required_for_request(request) -> bool:
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or not user.can_access_internal_panel:
        return False
    path = request.path
    return path not in SAFE_EXACT_PATHS and not path.startswith(SAFE_PREFIXES)


def _context_references(request) -> tuple[str, str, str, list[str]]:
    if not request.session.session_key:
        request.session.save()
    address = client_ip(request)
    current_user_agent_hash = _reference(request.META.get("HTTP_USER_AGENT", "")[:500])
    baseline = request.session.get("vinova_staff_device_reference")
    if not baseline:
        request.session["vinova_staff_device_reference"] = current_user_agent_hash
    reasons: list[str] = []
    if baseline and baseline != current_user_agent_hash:
        reasons.append("device_changed")
    return (
        _reference(request.session.session_key),
        _reference(address),
        current_user_agent_hash,
        reasons,
    )


def assess_staff_access(*, request, policy: SecurityPolicy) -> StaffAccessAssessment:
    """ES: Revalida riesgo en cada petición. EN: Re-evaluates risk on every request."""

    if policy.staff_access_mode == SecurityPolicy.StaffAccessMode.OFF or not staff_access_required_for_request(request):
        return StaffAccessAssessment(allowed=True)

    session_reference, ip_hash, user_agent_hash, reasons = _context_references(request)
    try:
        address = ipaddress.ip_address(client_ip(request))
    except ValueError:
        reasons.append("address_unavailable")
    else:
        networks = parse_trusted_staff_networks(policy.trusted_staff_networks)
        if not any(address in network for network in networks):
            reasons.append("untrusted_network")

    if not reasons:
        return StaffAccessAssessment(allowed=True)

    now = timezone.now()
    context = StaffAccessRequest.objects.filter(
        user=request.user,
        session_reference=session_reference,
        ip_hash=ip_hash,
        user_agent_hash=user_agent_hash,
    )
    context.filter(status=StaffAccessRequest.Status.APPROVED, access_expires_at__lte=now).update(
        status=StaffAccessRequest.Status.EXPIRED,
        updated_at=now,
    )
    approval = context.filter(
        status=StaffAccessRequest.Status.APPROVED,
        access_expires_at__gt=now,
    ).order_by("-access_expires_at").first()
    if approval:
        return StaffAccessAssessment(
            allowed=True,
            risk_reasons=tuple(reasons),
            session_reference=session_reference,
            ip_hash=ip_hash,
            user_agent_hash=user_agent_hash,
            approval=approval,
        )
    return StaffAccessAssessment(
        allowed=policy.staff_access_mode == SecurityPolicy.StaffAccessMode.MONITOR,
        monitored=policy.staff_access_mode == SecurityPolicy.StaffAccessMode.MONITOR,
        risk_reasons=tuple(reasons),
        session_reference=session_reference,
        ip_hash=ip_hash,
        user_agent_hash=user_agent_hash,
    )


def _active_global_approvers(*, exclude_user=None):
    now = timezone.now()
    role_filter = Q(
        user_roles__is_active=True,
        user_roles__branch__isnull=True,
        user_roles__role__is_active=True,
        user_roles__role__permissions__code="security.approve_staff_access",
    ) & (Q(user_roles__starts_at__isnull=True) | Q(user_roles__starts_at__lte=now)) & (
        Q(user_roles__expires_at__isnull=True) | Q(user_roles__expires_at__gt=now)
    )
    queryset = User.objects.filter(is_active=True).filter(Q(is_superuser=True) | role_filter).distinct()
    if exclude_user is not None:
        queryset = queryset.exclude(pk=exclude_user.pk)
    return queryset


def validate_staff_enforcement_readiness(*, actor, policy: SecurityPolicy) -> None:
    """Prevent enabling enforcement without a trusted route and independent approver."""

    networks = parse_trusted_staff_networks(policy.trusted_staff_networks)
    if not networks:
        raise ValidationError("Configura al menos una red corporativa o VPN antes de aplicar restricciones.")
    approvers = _active_global_approvers(exclude_user=actor).filter(security_profile__two_factor_enabled=True)
    if not approvers.exists():
        raise ValidationError(
            "Se necesita otro aprobador global activo, con permiso específico y 2FA, antes de aplicar restricciones."
        )


def _notify_approvers(access_request_id: int) -> None:
    """Create one minimal in-app notice; notification failure never grants access."""

    try:
        from apps.notifications.models import NotificationMessage, NotificationRecipient

        access_request = StaffAccessRequest.objects.select_related("user").get(pk=access_request_id)
        recipients = list(_active_global_approvers(exclude_user=access_request.user))
        if not recipients:
            return
        message, _ = NotificationMessage.objects.get_or_create(
            dedup_key=f"staff-access-request:{access_request.pk}",
            defaults={
                "title": "Solicitud de acceso Staff excepcional",
                "body": f"La cuenta {access_request.user.username} requiere una decisión temporal de acceso.",
                "message_type": NotificationMessage.MessageType.SYSTEM,
                "priority": NotificationMessage.Priority.HIGH,
                "status": NotificationMessage.Status.SENT,
            },
        )
        NotificationRecipient.objects.bulk_create(
            [
                NotificationRecipient(
                    notification=message,
                    recipient_type=NotificationRecipient.RecipientType.USER,
                    user=user,
                    display_name_snapshot=user.get_full_name() or user.username,
                    email_snapshot=user.email or "",
                )
                for user in recipients
            ],
            ignore_conflicts=True,
        )
    except Exception:  # noqa: BLE001 - access remains denied when notification infrastructure fails
        logger.exception("Unable to create Staff access approval notification")


@transaction.atomic
def ensure_staff_access_request(
    *, request, policy: SecurityPolicy, assessment: StaffAccessAssessment
) -> StaffAccessRequest:
    now = timezone.now()
    StaffAccessRequest.objects.filter(
        user=request.user,
        status=StaffAccessRequest.Status.PENDING,
        request_expires_at__lte=now,
    ).update(status=StaffAccessRequest.Status.EXPIRED, updated_at=now)
    lookup = {
        "user": request.user,
        "session_reference": assessment.session_reference,
        "ip_hash": assessment.ip_hash,
        "user_agent_hash": assessment.user_agent_hash,
        "status": StaffAccessRequest.Status.PENDING,
    }
    existing = StaffAccessRequest.objects.filter(**lookup, request_expires_at__gt=now).first()
    if existing:
        return existing
    recent = StaffAccessRequest.objects.filter(
        user=request.user,
        created_at__gte=now - timedelta(minutes=min(60, max(5, policy.staff_access_request_minutes))),
    ).count()
    if recent >= 3:
        raise PermissionDenied("Demasiadas solicitudes recientes de acceso Staff.")
    try:
        access_request = StaffAccessRequest.objects.create(
            **lookup,
            risk_reasons=list(assessment.risk_reasons),
            request_expires_at=now + timedelta(minutes=min(60, max(5, policy.staff_access_request_minutes))),
        )
    except IntegrityError:
        access_request = StaffAccessRequest.objects.get(**lookup)
    audit_log(
        user=request.user,
        action="security.staff_access.requested",
        target=access_request,
        after={"risk_reasons": list(assessment.risk_reasons)},
    )
    transaction.on_commit(lambda: _notify_approvers(access_request.pk), robust=True)
    return access_request


def _authority_level(user) -> int:
    if user.is_superuser:
        return 0
    level = user.active_role_assignments().aggregate(level=Min("role__level"))["level"]
    return level if level is not None else 65535


def _validate_decision_actor(*, actor, access_request: StaffAccessRequest, actor_2fa_verified: bool) -> None:
    if actor == access_request.user:
        raise PermissionDenied("No puedes aprobar tu propia solicitud.")
    if not actor_2fa_verified:
        raise PermissionDenied("La decisión requiere 2FA verificado en esta sesión.")
    if not actor.is_superuser:
        allowed = actor.active_role_assignments().filter(
            branch__isnull=True,
            role__permissions__code="security.approve_staff_access",
        ).exists()
        if not allowed:
            raise PermissionDenied("La decisión requiere el permiso global específico.")
    if _authority_level(actor) >= _authority_level(access_request.user):
        raise PermissionDenied("La decisión requiere una cuenta de rango superior.")


@transaction.atomic
def decide_staff_access(
    *, access_request_id: int, actor, approve: bool, note: str, actor_2fa_verified: bool
) -> StaffAccessRequest:
    access_request = StaffAccessRequest.objects.select_for_update().select_related("user").get(pk=access_request_id)
    _validate_decision_actor(
        actor=actor,
        access_request=access_request,
        actor_2fa_verified=actor_2fa_verified,
    )
    now = timezone.now()
    if access_request.status != StaffAccessRequest.Status.PENDING:
        raise ValidationError("La solicitud ya fue resuelta.")
    if access_request.request_expires_at <= now:
        access_request.status = StaffAccessRequest.Status.EXPIRED
        access_request.save(update_fields=["status", "updated_at"])
        raise ValidationError("La solicitud expiró; la cuenta debe generar una nueva.")
    policy = SecurityPolicy.current()
    access_request.status = StaffAccessRequest.Status.APPROVED if approve else StaffAccessRequest.Status.REJECTED
    access_request.decided_by = actor
    access_request.decided_at = now
    access_request.decision_note = (note or "")[:500]
    access_request.access_expires_at = (
        now + timedelta(minutes=min(1440, max(5, policy.staff_access_approval_minutes))) if approve else None
    )
    access_request.save(
        update_fields=[
            "status",
            "decided_by",
            "decided_at",
            "decision_note",
            "access_expires_at",
            "updated_at",
        ]
    )
    audit_log(
        user=actor,
        action="security.staff_access.approved" if approve else "security.staff_access.rejected",
        target=access_request,
        after={"requester_id": access_request.user_id, "expires_at": access_request.access_expires_at},
    )
    return access_request


@transaction.atomic
def revoke_staff_access(*, access_request_id: int, actor, actor_2fa_verified: bool) -> StaffAccessRequest:
    access_request = StaffAccessRequest.objects.select_for_update().select_related("user").get(pk=access_request_id)
    _validate_decision_actor(
        actor=actor,
        access_request=access_request,
        actor_2fa_verified=actor_2fa_verified,
    )
    if access_request.status != StaffAccessRequest.Status.APPROVED:
        raise ValidationError("Solo se puede revocar una aprobación vigente.")
    if not access_request.access_expires_at or access_request.access_expires_at <= timezone.now():
        access_request.status = StaffAccessRequest.Status.EXPIRED
        access_request.save(update_fields=["status", "updated_at"])
        raise ValidationError("La aprobación ya expiró.")
    access_request.status = StaffAccessRequest.Status.REVOKED
    access_request.decided_by = actor
    access_request.decided_at = timezone.now()
    access_request.save(update_fields=["status", "decided_by", "decided_at", "updated_at"])
    audit_log(
        user=actor,
        action="security.staff_access.revoked",
        target=access_request,
        after={"requester_id": access_request.user_id},
    )
    return access_request


@transaction.atomic
def cancel_staff_access(*, access_request_id: int, actor) -> StaffAccessRequest:
    access_request = StaffAccessRequest.objects.select_for_update().get(pk=access_request_id, user=actor)
    if access_request.status != StaffAccessRequest.Status.PENDING:
        raise ValidationError("La solicitud ya no está pendiente.")
    access_request.status = StaffAccessRequest.Status.CANCELLED
    access_request.decided_at = timezone.now()
    access_request.save(update_fields=["status", "decided_at", "updated_at"])
    audit_log(user=actor, action="security.staff_access.cancelled", target=access_request)
    return access_request


def audit_monitored_staff_risk(*, request, assessment: StaffAccessAssessment) -> None:
    marker = _reference("|".join((assessment.ip_hash, assessment.user_agent_hash, *assessment.risk_reasons)))
    if request.session.get("vinova_staff_risk_marker") == marker:
        return
    request.session["vinova_staff_risk_marker"] = marker
    audit_log(
        user=request.user,
        action="security.staff_access.monitored",
        target=request.user,
        result=AuditLog.Result.SUCCESS,
        after={"risk_reasons": list(assessment.risk_reasons)},
    )
