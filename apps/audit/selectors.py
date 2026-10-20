"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de auditoría.

EN: This module implements authorization-aware read queries for the audit domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the audit domain.
"""

from __future__ import annotations

from datetime import datetime, time
from uuid import UUID

from django.db.models import Count, Q
from django.utils import timezone

from apps.accounts.scopes import accessible_branch_ids
from apps.audit.models import AuditLog, SecurityAlert


def scoped_audit_queryset(user, *, permission_code="audit.view"):
    qs = AuditLog.objects.select_related("user", "branch", "customer")
    branch_ids = accessible_branch_ids(user, permission_codes=(permission_code,))
    if branch_ids is None:
        return qs
    return qs.filter(Q(branch_id__in=branch_ids) | Q(user=user))


def filtered_audit_queryset(user, cleaned_data, *, permission_code="audit.view"):
    """Apply validated search filters to the actor's scoped audit queryset."""

    qs = scoped_audit_queryset(user, permission_code=permission_code)
    q = cleaned_data.get("q")
    if q:
        qs = qs.filter(
            Q(action__icontains=q)
            | Q(object_repr__icontains=q)
            | Q(object_id__icontains=q)
            | Q(content_type_label__icontains=q)
            | Q(username_snapshot__icontains=q)
            | Q(user_display_snapshot__icontains=q)
            | Q(ip_address__icontains=q)
        )
        try:
            identifier = UUID(str(q))
        except (TypeError, ValueError):
            identifier = None
        if identifier:
            qs = qs | scoped_audit_queryset(user, permission_code=permission_code).filter(Q(event_id=identifier) | Q(request_id=identifier))
    for field in ("category", "severity", "result"):
        if cleaned_data.get(field):
            qs = qs.filter(**{field: cleaned_data[field]})
    if cleaned_data.get("action"):
        qs = qs.filter(action__icontains=cleaned_data["action"])
    if cleaned_data.get("user"):
        qs = qs.filter(user=cleaned_data["user"])
    if cleaned_data.get("branch"):
        qs = qs.filter(branch=cleaned_data["branch"])
    if cleaned_data.get("object_type"):
        qs = qs.filter(content_type_label__icontains=cleaned_data["object_type"])
    if cleaned_data.get("ip_address"):
        qs = qs.filter(ip_address__icontains=cleaned_data["ip_address"])
    if cleaned_data.get("date_from"):
        start = timezone.make_aware(datetime.combine(cleaned_data["date_from"], time.min))
        qs = qs.filter(occurred_at__gte=start)
    if cleaned_data.get("date_to"):
        end = timezone.make_aware(datetime.combine(cleaned_data["date_to"], time.max))
        qs = qs.filter(occurred_at__lte=end)
    return qs.distinct()


def scoped_alert_queryset(user, *, permission_code="audit.view"):
    qs = SecurityAlert.objects.select_related("audit_log", "user", "branch", "assigned_to", "resolved_by")
    branch_ids = accessible_branch_ids(user, permission_codes=(permission_code,))
    if branch_ids is None:
        return qs
    return qs.filter(Q(branch_id__in=branch_ids) | Q(user=user))


def filtered_alert_queryset(user, cleaned_data, *, permission_code="audit.view"):
    qs = scoped_alert_queryset(user, permission_code=permission_code)
    if cleaned_data.get("q"):
        q = cleaned_data["q"]
        qs = qs.filter(Q(code__icontains=q) | Q(title__icontains=q) | Q(description__icontains=q) | Q(user__username__icontains=q))
    if cleaned_data.get("severity"):
        qs = qs.filter(severity=cleaned_data["severity"])
    if cleaned_data.get("status"):
        qs = qs.filter(status=cleaned_data["status"])
    if cleaned_data.get("branch"):
        qs = qs.filter(branch=cleaned_data["branch"])
    return qs


def audit_dashboard_metrics(user):
    qs = scoped_audit_queryset(user)
    alert_qs = scoped_alert_queryset(user)
    since = timezone.now() - timezone.timedelta(days=30)
    return {
        "total": qs.count(),
        "last_30_days": qs.filter(occurred_at__gte=since).count(),
        "high_risk": qs.filter(severity__in=[AuditLog.Severity.HIGH, AuditLog.Severity.CRITICAL], occurred_at__gte=since).count(),
        "denied": qs.filter(result=AuditLog.Result.DENIED, occurred_at__gte=since).count(),
        "open_alerts": alert_qs.filter(status__in=[SecurityAlert.Status.OPEN, SecurityAlert.Status.IN_REVIEW]).count(),
        "top_actions": list(qs.filter(occurred_at__gte=since).values("action").annotate(total=Count("id")).order_by("-total")[:8]),
    }
