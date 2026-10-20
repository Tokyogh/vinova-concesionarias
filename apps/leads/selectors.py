"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de CRM y leads.

EN: This module implements authorization-aware read queries for the leads domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the leads domain.
"""

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from apps.accounts.scopes import (
    accessible_branch_ids,
    accessible_branches_queryset,
    accessible_users_queryset,
    active_role_assignments,
)
from apps.leads.models import Lead
from apps.vehicles.models import Vehicle


LEAD_SCOPE_PERMISSIONS = ("leads.view", "leads.manage", "leads.assign", "leads.export")


def scoped_lead_queryset(user, *, permission_codes=LEAD_SCOPE_PERMISSIONS):
    qs = Lead.objects.filter(is_deleted=False).select_related(
        "vehicle", "vehicle__brand", "vehicle__model", "branch", "assigned_advisor", "customer", "linked_sale"
    ).prefetch_related("activities", "test_drives")
    branch_ids = accessible_branch_ids(user, permission_codes=permission_codes)
    if branch_ids is None:
        return qs
    if not branch_ids:
        return qs.none()
    qs = qs.filter(branch_id__in=branch_ids)
    assignments = active_role_assignments(user, permission_codes=permission_codes)
    if assignments.exists() and not assignments.exclude(role__code="vendedor").exists():
        qs = qs.filter(Q(assigned_advisor=user) | Q(assigned_advisor__isnull=True))
    return qs


def accessible_lead_branches_queryset(user, *, permission_codes=LEAD_SCOPE_PERMISSIONS):
    return accessible_branches_queryset(user, permission_codes=permission_codes)


def accessible_lead_advisors_queryset(user, *, permission_codes=LEAD_SCOPE_PERMISSIONS):
    return accessible_users_queryset(user, permission_codes=permission_codes)


def accessible_lead_vehicles_queryset(user, *, permission_codes=LEAD_SCOPE_PERMISSIONS):
    branch_ids = accessible_branch_ids(user, permission_codes=permission_codes)
    queryset = Vehicle.objects.filter(is_deleted=False)
    if branch_ids is not None:
        if not branch_ids:
            return queryset.none()
        queryset = queryset.filter(branch_id__in=branch_ids)
    return queryset.select_related("brand", "model", "model__brand").order_by("brand__name", "model__name", "-year")


def filtered_lead_queryset(user, cleaned: dict):
    qs = scoped_lead_queryset(user)
    q = (cleaned.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(code__icontains=q) | Q(full_name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q)
            | Q(whatsapp__icontains=q) | Q(city__icontains=q) | Q(vehicle__internal_code__icontains=q)
            | Q(vehicle__brand__name__icontains=q) | Q(vehicle__model__name__icontains=q)
        )
    for key in ["status", "priority", "source", "request_type"]:
        if cleaned.get(key):
            qs = qs.filter(**{key: cleaned[key]})
    if cleaned.get("branch"):
        qs = qs.filter(branch=cleaned["branch"])
    if cleaned.get("advisor"):
        qs = qs.filter(assigned_advisor=cleaned["advisor"])
    if cleaned.get("overdue"):
        qs = qs.filter(next_follow_up_at__lt=timezone.now()).exclude(status__in=[Lead.Status.WON, Lead.Status.LOST])
    ordering = {
        "newest": ("-created_at",), "oldest": ("created_at",),
        "follow_up": ("next_follow_up_at", "-created_at"),
    }.get(cleaned.get("sort"), ("-priority", "next_follow_up_at", "-created_at"))
    return qs.order_by(*ordering)


def lead_detail_queryset(user, *, permission_codes=LEAD_SCOPE_PERMISSIONS):
    return scoped_lead_queryset(user, permission_codes=permission_codes).prefetch_related(
        "activities__created_by", "test_drives__vehicle", "test_drives__advisor"
    )


def pipeline_columns(user):
    qs = scoped_lead_queryset(user).exclude(status=Lead.Status.LOST).order_by("-score", "next_follow_up_at", "-created_at")
    return [{"code": code, "label": label, "leads": qs.filter(status=code)[:80], "count": qs.filter(status=code).count()} for code, label in Lead.Status.choices if code != Lead.Status.LOST]


def lead_metrics(user):
    qs = scoped_lead_queryset(user)
    open_qs = qs.exclude(status__in=[Lead.Status.WON, Lead.Status.LOST])
    return {
        "total": qs.count(),
        "new": qs.filter(status=Lead.Status.NEW).count(),
        "open": open_qs.count(),
        "won": qs.filter(status=Lead.Status.WON).count(),
        "lost": qs.filter(status=Lead.Status.LOST).count(),
        "overdue": open_qs.filter(next_follow_up_at__lt=timezone.now()).count(),
        "unassigned": open_qs.filter(assigned_advisor__isnull=True).count(),
    }
