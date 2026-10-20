"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de auditoría.

EN: This module implements business services and transactional effects for the audit domain.

Contexto existente / Existing context:
Transactional business services for the audit domain.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.audit.context import get_audit_context
from apps.audit.models import AuditLog, SecurityAlert

SENSITIVE_KEYS = {
    "password", "password1", "password2", "old_password", "new_password",
    "token", "access_token", "refresh_token", "secret", "api_key", "authorization",
    "certificate_password", "clave", "private_key", "sessionid", "csrfmiddlewaretoken",
}

ACTION_RULES = {
    "login.success": (AuditLog.Category.AUTHENTICATION, AuditLog.Severity.INFO, AuditLog.Result.SUCCESS),
    "login.failed": (AuditLog.Category.AUTHENTICATION, AuditLog.Severity.HIGH, AuditLog.Result.FAILED),
    "logout": (AuditLog.Category.AUTHENTICATION, AuditLog.Severity.INFO, AuditLog.Result.SUCCESS),
    "security.permission_denied": (AuditLog.Category.AUTHORIZATION, AuditLog.Severity.HIGH, AuditLog.Result.DENIED),
    "security.server_error": (AuditLog.Category.SECURITY, AuditLog.Severity.CRITICAL, AuditLog.Result.FAILED),
    "security.login_rate_limited": (AuditLog.Category.AUTHENTICATION, AuditLog.Severity.HIGH, AuditLog.Result.DENIED),
    "security.2fa.enabled": (AuditLog.Category.SECURITY, AuditLog.Severity.HIGH, AuditLog.Result.SUCCESS),
    "security.2fa.disabled": (AuditLog.Category.SECURITY, AuditLog.Severity.HIGH, AuditLog.Result.SUCCESS),
    "security.2fa.failed": (AuditLog.Category.AUTHENTICATION, AuditLog.Severity.HIGH, AuditLog.Result.FAILED),
    "security.2fa.verified": (AuditLog.Category.AUTHENTICATION, AuditLog.Severity.INFO, AuditLog.Result.SUCCESS),
    "security.session.revoked": (AuditLog.Category.SECURITY, AuditLog.Severity.HIGH, AuditLog.Result.SUCCESS),
    "security.policy.updated": (AuditLog.Category.CONFIGURATION, AuditLog.Severity.HIGH, AuditLog.Result.SUCCESS),
    "continuity.policy.updated": (AuditLog.Category.CONFIGURATION, AuditLog.Severity.HIGH, AuditLog.Result.SUCCESS),
    "security.password.changed": (AuditLog.Category.SECURITY, AuditLog.Severity.HIGH, AuditLog.Result.SUCCESS),
    "accounts.password.admin_set": (AuditLog.Category.SECURITY, AuditLog.Severity.HIGH, AuditLog.Result.SUCCESS),
    "accounts.role.remove": (AuditLog.Category.AUTHORIZATION, AuditLog.Severity.HIGH, AuditLog.Result.SUCCESS),
    "accounts.user.toggle_active": (AuditLog.Category.SECURITY, AuditLog.Severity.HIGH, AuditLog.Result.SUCCESS),
    "documents.private.download": (AuditLog.Category.DOCUMENT, AuditLog.Severity.MEDIUM, AuditLog.Result.SUCCESS),
    "invoices.void": (AuditLog.Category.SALES, AuditLog.Severity.HIGH, AuditLog.Result.SUCCESS),
}


def _json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if hasattr(value, "pk"):
        return str(value.pk)
    return str(value)


def sanitize_payload(value: Any, *, key: str = "") -> Any:
    normalized_key = key.lower().strip()
    if normalized_key in SENSITIVE_KEYS or any(token in normalized_key for token in ("password", "secret", "token", "private_key")):
        return "[REDACTADO]"
    if isinstance(value, dict):
        return {str(k): sanitize_payload(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [sanitize_payload(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return _json_safe(value)


def _infer_rule(action: str):
    if action in ACTION_RULES:
        return ACTION_RULES[action]
    prefix = action.split(".", 1)[0]
    category_map = {
        "accounts": AuditLog.Category.AUTHORIZATION,
        "documents": AuditLog.Category.DOCUMENT,
        "inventory": AuditLog.Category.INVENTORY,
        "sales": AuditLog.Category.SALES,
        "invoices": AuditLog.Category.SALES,
        "imports": AuditLog.Category.IMPORT,
        "enterprise": AuditLog.Category.CONFIGURATION,
        "sri": AuditLog.Category.CONFIGURATION,
        "reports": AuditLog.Category.REPORT,
        "audit": AuditLog.Category.REPORT,
        "quality": AuditLog.Category.REPORT,
        "security": AuditLog.Category.SECURITY,
    }
    category = category_map.get(prefix, AuditLog.Category.DATA_CHANGE)
    severity = AuditLog.Severity.MEDIUM if any(word in action for word in ("delete", "archive", "void", "password", "permission", "role")) else AuditLog.Severity.INFO
    return category, severity, AuditLog.Result.SUCCESS


def _user_snapshot(user) -> tuple[str, str, list[dict[str, Any]]]:
    if not getattr(user, "is_authenticated", False):
        return "", "", []
    roles = list(
        user.user_roles.filter(is_active=True, role__is_active=True)
        .select_related("role", "branch")
        .values("role__code", "role__name", "branch_id", "branch__name")
    )
    display = user.get_full_name().strip() or user.username
    return user.username, display, roles


def _resolve_customer(target):
    if target is None:
        return None
    if target._meta.label_lower == "customers.customer":
        return target
    customer = getattr(target, "customer", None)
    return customer if getattr(customer, "pk", None) else None


def _hash_payload(data: dict[str, Any]) -> str:
    encoded = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=_json_safe).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _should_create_alert(log: AuditLog) -> bool:
    if log.severity == AuditLog.Severity.CRITICAL:
        return True
    return log.action in {"login.failed", "security.login_rate_limited", "security.permission_denied", "security.2fa.failed", "security.2fa.disabled", "security.session.revoked", "accounts.user.toggle_active", "accounts.password.admin_set"}


def _alert_title(log: AuditLog) -> str:
    titles = {
        "login.failed": "Intento de inicio de sesión fallido",
        "security.permission_denied": "Acceso denegado a una sección protegida",
        "security.server_error": "Error crítico del servidor",
        "security.login_rate_limited": "Inicio de sesión bloqueado por rate limiting",
        "security.2fa.failed": "Código de segundo factor incorrecto",
        "security.2fa.disabled": "Autenticación en dos pasos desactivada",
        "security.session.revoked": "Sesión revocada",
        "accounts.user.toggle_active": "Cambio de estado de una cuenta",
        "accounts.password.admin_set": "Contraseña modificada por administración",
    }
    return titles.get(log.action, f"Evento de seguridad: {log.action}")


@transaction.atomic
def audit_log(
    *,
    user=None,
    action: str,
    target=None,
    before=None,
    after=None,
    metadata=None,
    category: str | None = None,
    severity: str | None = None,
    result: str | None = None,
    branch=None,
    customer=None,
    is_sensitive: bool = False,
) -> AuditLog:
    """ES: Ejecuta la operación «audit log» dentro del dominio de auditoría. Además, registra efectos auditables.

    EN: Executes the «audit log» operation within the audit domain. It also records auditable effects.
    """

    inferred_category, inferred_severity, inferred_result = _infer_rule(action)
    context = get_audit_context()
    label = oid = rep = ""
    if target is not None:
        label = f"{target._meta.app_label}.{target._meta.model_name}"
        oid = str(target.pk or "")
        rep = str(target)[:250]
    username, display, roles = _user_snapshot(user)
    resolved_branch = branch or context.get("branch") or getattr(user, "branch", None)
    if resolved_branch is None and roles:
        role_branch_ids = {item.get("branch_id") for item in roles if item.get("branch_id")}
        if len(role_branch_ids) == 1:
            from apps.branches.models import Branch
            resolved_branch = Branch.objects.filter(pk=next(iter(role_branch_ids))).first()
    resolved_customer = customer or _resolve_customer(target)
    occurred_at = timezone.now()
    previous = AuditLog.objects.order_by("-occurred_at", "-id").only("entry_hash").first()
    previous_hash = previous.entry_hash if previous and previous.entry_hash else ""
    sanitized_before = sanitize_payload(before or {})
    sanitized_after = sanitize_payload(after or {})
    sanitized_metadata = sanitize_payload(metadata or {})
    request_id = context.get("request_id")
    if request_id and not isinstance(request_id, UUID):
        try:
            request_id = UUID(str(request_id))
        except (TypeError, ValueError):
            request_id = None

    log = AuditLog(
        occurred_at=occurred_at,
        user=user if getattr(user, "is_authenticated", False) else None,
        username_snapshot=username,
        user_display_snapshot=display,
        role_snapshot=roles,
        branch=resolved_branch if getattr(resolved_branch, "pk", None) else None,
        customer=resolved_customer if getattr(resolved_customer, "pk", None) else None,
        action=action,
        category=category or inferred_category,
        severity=severity or inferred_severity,
        result=result or inferred_result,
        object_repr=rep,
        content_type_label=label,
        object_id=oid,
        request_id=request_id,
        ip_address=context.get("ip_address") or None,
        user_agent=(context.get("user_agent") or "")[:2000],
        http_method=(context.get("http_method") or "")[:12],
        request_path=(context.get("request_path") or "")[:500],
        before=sanitized_before,
        after=sanitized_after,
        metadata=sanitized_metadata,
        is_sensitive=is_sensitive or action.startswith("documents.private.") or action.startswith("sri."),
        previous_hash=previous_hash,
    )
    integrity_payload = {
        "event_id": str(log.event_id),
        "occurred_at": occurred_at.isoformat(),
        "user_id": getattr(log.user, "pk", None),
        "action": log.action,
        "category": log.category,
        "severity": log.severity,
        "result": log.result,
        "object": [log.content_type_label, log.object_id],
        "request_id": str(log.request_id or ""),
        "before": log.before,
        "after": log.after,
        "metadata": log.metadata,
        "previous_hash": previous_hash,
    }
    log.entry_hash = _hash_payload(integrity_payload)
    log.save(force_insert=True)

    if _should_create_alert(log):
        SecurityAlert.objects.create(
            audit_log=log,
            code=log.action,
            title=_alert_title(log),
            description=f"Usuario: {log.user_display_snapshot or log.username_snapshot or 'No identificado'}. Ruta: {log.request_path or 'N/D'}.",
            severity=log.severity if log.severity in {AuditLog.Severity.HIGH, AuditLog.Severity.CRITICAL} else AuditLog.Severity.HIGH,
            branch=log.branch,
            user=log.user,
            metadata={"request_id": str(log.request_id or ""), "ip": str(log.ip_address or "")},
        )
    return log


def verify_audit_chain(*, queryset=None, strict_links: bool = False) -> dict[str, Any]:
    logs = (queryset or AuditLog.objects.all()).order_by("occurred_at", "id")
    previous_in_scope_hash = ""
    checked = 0
    issues: list[dict[str, Any]] = []
    for log in logs.iterator(chunk_size=500):
        payload = {
            "event_id": str(log.event_id),
            "occurred_at": log.occurred_at.isoformat(),
            "user_id": log.user_id,
            "action": log.action,
            "category": log.category,
            "severity": log.severity,
            "result": log.result,
            "object": [log.content_type_label, log.object_id],
            "request_id": str(log.request_id or ""),
            "before": log.before,
            "after": log.after,
            "metadata": log.metadata,
            "previous_hash": log.previous_hash,
        }
        expected = _hash_payload(payload)
        invalid_hash = log.entry_hash != expected
        invalid_link = strict_links and checked > 0 and log.previous_hash != previous_in_scope_hash
        if invalid_hash or invalid_link:
            issues.append({
                "event_id": str(log.event_id),
                "action": log.action,
                "occurred_at": log.occurred_at.isoformat(),
                "invalid_hash": invalid_hash,
                "invalid_link": invalid_link,
            })
        previous_in_scope_hash = log.entry_hash or ""
        checked += 1
    return {"checked": checked, "valid": not issues, "issues": issues[:100], "last_hash": previous_in_scope_hash}
